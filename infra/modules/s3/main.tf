resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.name_prefix}-data-lake"

  tags = { Name = "${var.name_prefix}-data-lake" }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "intelligent-tiering-delta"
    status = "Enabled"

    filter {
      prefix = "delta/"
    }

    transition {
      days          = 90
      storage_class = "INTELLIGENT_TIERING"
    }
  }

  rule {
    id     = "expire-raw-xlsx"
    status = "Enabled"

    filter {
      prefix = "raw/xlsx/"
    }

    expiration {
      days = 365
    }
  }
}
