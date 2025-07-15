locals {
  infoblox_ami_id = "ami-008772a29d4c2f558"
}

# MGMT NIC (Primary NIC)
resource "aws_network_interface" "gm_mgmt" {
  subnet_id       = aws_subnet.public.id
  private_ips     = ["10.100.0.201"]
  security_groups = [aws_security_group.rdp_sg.id]

  tags = {
    Name = "gm-mgmt-nic"
  }
}

# LAN1 NIC (Private-only)
resource "aws_network_interface" "gm_lan1" {
  subnet_id       = aws_subnet.public.id
  private_ips     = ["10.100.0.200"]
  security_groups = [aws_security_group.rdp_sg.id]

  tags = {
    Name = "gm-lan1-nic"
  }
}

# GM EC2 Instance
resource "aws_instance" "gm" {
  ami           = local.infoblox_ami_id
  instance_type = "m5.2xlarge"
  key_name      = aws_key_pair.rdp.key_name

  network_interface {
    network_interface_id = aws_network_interface.gm_mgmt.id
    device_index         = 0
  }

  network_interface {
    network_interface_id = aws_network_interface.gm_lan1.id
    device_index         = 1
  }

  user_data = <<-EOF
    #infoblox-config
    temp_license: nios IB-V825 enterprise dns dhcp cloud
    remote_console_enabled: y
    default_admin_password: "Proba123!"
    lan1:
      v4_addr: 10.100.0.200
      v4_netmask: 255.255.255.0
      v4_gw: 10.100.0.1
    mgmt:
      v4_addr: 10.100.0.201
      v4_netmask: 255.255.255.0
      v4_gw: 10.100.0.1
  EOF

  tags = {
    Name = "Infoblox-GM"
  }

  depends_on = [aws_internet_gateway.gw]
}

# EIP only for LAN NIC
resource "aws_eip" "gm_eip" {
  domain = "vpc"
  tags = {
    Name = "gm-eip-mgmt"
  }
}

resource "aws_eip_association" "gm_eip_assoc_mgmt" {
  network_interface_id = aws_network_interface.gm_lan1.id
  allocation_id        = aws_eip.gm_eip.id
  private_ip_address   = "10.100.0.200"
}
