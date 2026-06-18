output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = [aws_subnet.public_az1.id, aws_subnet.public_az2.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.private_az1.id, aws_subnet.private_az2.id]
}

output "alb_sg_id" {
  value = aws_security_group.alb.id
}

output "mcp_server_sg_id" {
  value = aws_security_group.mcp_server.id
}

output "sharing_server_sg_id" {
  value = aws_security_group.sharing_server.id
}

output "web_app_sg_id" {
  value = aws_security_group.web_app.id
}
