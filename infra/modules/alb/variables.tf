variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "alb_sg_id" {
  type = string
}

variable "certificate_arn" {
  type    = string
  default = ""
}

variable "web_app_target_group_required" {
  # Placeholder — web target group is always created; variable kept for clarity
  type    = bool
  default = true
}
