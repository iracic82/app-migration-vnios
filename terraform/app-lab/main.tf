terraform {
  required_providers {
    bloxone = {
      source  = "infobloxopen/bloxone"
      version = ">= 1.5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "bloxone" {
  csp_url = "https://csp.infoblox.com"
  api_key = var.ddi_api_key

  default_tags = {
    managed_by = "terraform"
    site       = "Site A"
  }
}

# -----------------------------
# Variables
# -----------------------------
variable "ddi_api_key" {}
variable "aws_region" {
  default = "eu-central-1"
}
variable "availability_zone" {
  default = "eu-central-1a"
}
variable "project_name" {
  default = "infoblox-aws-integration"
}

# -----------------------------
# Lookup Realm and Federated Block
# -----------------------------
data "bloxone_federation_federated_realms" "acme" {
  filters = {
    name = "ACME Corporation"
  }
}

data "bloxone_federation_federated_blocks" "aws_block" {
  filters = {
    name = "AWS"
  }
}

# -----------------------------
# Create Infoblox IPAM Resources
# -----------------------------
resource "bloxone_ipam_ip_space" "ip_space_acme" {
  name    = "acme-ip-space"
  comment = "IP space for ACME via Terraform"

  default_realms = [data.bloxone_federation_federated_realms.acme.results[0].id]

  tags = {
    project     = var.project_name
    environment = "dev"
  }
}

resource "bloxone_ipam_address_block" "block_aws_vpc" {
  address = "10.100.0.0"
  cidr    = 24
  name    = "aws-vpc-block"
  space   = bloxone_ipam_ip_space.ip_space_acme.id

  federated_realms = [data.bloxone_federation_federated_realms.acme.results[0].id]

  tags = {
    origin          = "federated"
    provisioned_by  = "terraform"
    block_type      = "materialized"
  }
}

resource "bloxone_ipam_subnet" "subnet_aws_vpc" {
  next_available_id = bloxone_ipam_address_block.block_aws_vpc.id
  cidr              = 24
  space             = bloxone_ipam_ip_space.ip_space_acme.id

  name = "aws-vpc-subnet"

  tags = {
    network_type = "vpc-subnet"
    cloud        = "aws"
  }
}

resource "bloxone_ipam_range" "aws_safe_range" {
  name   = "aws-safe-range"
  start  = "10.100.0.10"
  end    = "10.100.0.50"
  space  = bloxone_ipam_ip_space.ip_space_acme.id

  tags = {
    reserved = "skip-aws-reserved"
  }
}




# -------------------------------------
# Existing AWS VPC and Subnet (by Name Tag)
# -------------------------------------
data "aws_vpc" "existing_main" {
  filter {
    name   = "tag:Name"
    values = ["Infoblox-Lab"]  # <- must exactly match the Value above
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

data "aws_subnet" "existing_public" {
  filter {
    name   = "tag:Name"
    values = ["public-subnet"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}
data "aws_security_group" "app_sg" {
  filter {
    name   = "tag:Name"
    values = ["app-sg"]
  }

  vpc_id = data.aws_vpc.existing_main.id
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

data "aws_key_pair" "rdp" {
  key_name = "instruqt-dc-key"
}

# -------------------------------------
# Lookup Infoblox Subnet by Name
# -------------------------------------
data "bloxone_ipam_subnets" "existing" {
  filters = {
    name = "aws-vpc-subnet"
  }
}

# -------------------------------------
# Allocate an IP from Infoblox
# -------------------------------------
resource "bloxone_ipam_address" "app2_ip" {
  next_available_id = bloxone_ipam_range.aws_safe_range.id
  space             = bloxone_ipam_ip_space.ip_space_acme.id
  comment           = "App2 static IP from safe AWS range"

  tags = {
    environment = "dev"
    provisioned = "terraform"
    use         = "app2"
  }
}

# -------------------------------------
# Create new ENI with allocated IP
# -------------------------------------
resource "aws_network_interface" "app2_eni" {
  subnet_id       = data.aws_subnet.existing_public.id
  private_ips     = [bloxone_ipam_address.app2_ip.address]
  security_groups = [data.aws_security_group.app_sg.id]

  tags = {
    Name = "app2-eni"
  }
}

# -------------------------------------
# Launch App2 EC2 Instance with Docker App
# -------------------------------------
resource "aws_instance" "app2" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.small"
  key_name      = data.aws_key_pair.rdp.key_name

  network_interface {
    network_interface_id = aws_network_interface.app2_eni.id
    device_index         = 0
  }

  user_data = <<-EOF
              #!/bin/bash
              sudo apt update -y
              sudo apt install -y docker.io
              sudo systemctl enable docker
              sudo hostnamectl set-hostname new-location

              HOSTNAME=$(hostname)
              PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

              sudo docker run -d \
                -p 5080:5080 \
                -e EC2_HOSTNAME="$HOSTNAME" \
                -e EC2_IP="$PRIVATE_IP" \
                iracic82/infoblox-migration-demo:latest
              EOF

  tags = {
    Name = "app2"
    Role = "app"
  }
}

# -------------------------------------
# Output the IP for convenience
# -------------------------------------
output "app2_ip" {
  value = bloxone_ipam_address.app2_ip.address
}
