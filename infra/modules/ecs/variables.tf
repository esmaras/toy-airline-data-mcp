variable "name_prefix" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "sharing_server_sg_id" {
  type = string
}

variable "mcp_server_sg_id" {
  type = string
}

variable "task_execution_role_arn" {
  type = string
}

variable "sharing_server_task_role_arn" {
  type = string
}

variable "mcp_server_task_role_arn" {
  type = string
}

variable "sharing_server_image" {
  type = string
}

variable "mcp_server_image" {
  type = string
}

variable "data_lake_bucket" {
  type = string
}

variable "mcp_target_group_arn" {
  type = string
}

variable "web_app_image" {
  type = string
}

variable "web_app_sg_id" {
  type = string
}

variable "web_target_group_arn" {
  type = string
}

variable "web_app_task_role_arn" {
  type = string
}

variable "anthropic_api_key_ssm_arn" {
  type = string
}
