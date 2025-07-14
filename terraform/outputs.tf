# Outputs
output "client_public_ip" {
  description = "Public IP for Windows client VM (RDP access)"
  value       = aws_eip.client_eip.public_ip
}

output "flask_app_url" {
  description = "URL to access the Flask app on the app-old instance"
  value       = "http://${aws_route53_record.app.fqdn}:5000"
}

output "ssh_access_to_app" {
  description = "SSH command to access the Dockerized Flask app instance"
  value       = "ssh -i instruqt-dc-key.pem ubuntu@${aws_eip.app_eip.public_ip}"
}
