locals {
  name_prefix = "${var.project}-${var.environment}"
}

module "networking" {
  source      = "./modules/networking"
  name_prefix = local.name_prefix
  vpc_cidr    = var.vpc_cidr
}

module "s3" {
  source      = "./modules/s3"
  name_prefix = local.name_prefix
  environment = var.environment
}

module "iam" {
  source                    = "./modules/iam"
  name_prefix               = local.name_prefix
  data_lake_bucket_arn      = module.s3.bucket_arn
  anthropic_api_key_ssm_arn = var.anthropic_api_key_ssm_arn
}

module "ecr" {
  source      = "./modules/ecr"
  name_prefix = local.name_prefix
}

module "alb" {
  source           = "./modules/alb"
  name_prefix      = local.name_prefix
  vpc_id           = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  alb_sg_id        = module.networking.alb_sg_id
  certificate_arn  = var.certificate_arn
}

module "ecs" {
  source                        = "./modules/ecs"
  name_prefix                   = local.name_prefix
  aws_region                    = var.aws_region
  vpc_id                        = module.networking.vpc_id
  private_subnet_ids            = module.networking.private_subnet_ids
  sharing_server_sg_id          = module.networking.sharing_server_sg_id
  mcp_server_sg_id              = module.networking.mcp_server_sg_id
  web_app_sg_id                 = module.networking.web_app_sg_id
  task_execution_role_arn       = module.iam.task_execution_role_arn
  sharing_server_task_role_arn  = module.iam.sharing_server_task_role_arn
  mcp_server_task_role_arn      = module.iam.mcp_server_task_role_arn
  web_app_task_role_arn         = module.iam.web_app_task_role_arn
  sharing_server_image          = var.sharing_server_image
  mcp_server_image              = var.mcp_server_image
  web_app_image                 = var.web_app_image
  data_lake_bucket              = module.s3.bucket_name
  mcp_target_group_arn          = module.alb.mcp_target_group_arn
  web_target_group_arn          = module.alb.web_target_group_arn
  anthropic_api_key_ssm_arn     = var.anthropic_api_key_ssm_arn
}
