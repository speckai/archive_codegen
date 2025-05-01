terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
  backend "s3" {
    bucket         = "speck-terraform-state"
    key            = "speck/terraform.tfstate"
    region         = "us-west-1"
    dynamodb_table = "speck-terraform-state-lock"
  }
}

provider "aws" {
  region = "us-west-1"
}
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Redis cluster
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "speck-redis"
  engine              = "redis"
  node_type           = "cache.t3.micro"
  num_cache_nodes     = 1
  port                = 6379
  parameter_group_name = "default.redis7"
}

# Assets S3 bucket
resource "aws_s3_bucket" "assets" {
  bucket = "assets.speck.sh"
}

# Block all public access at bucket level - we'll use bucket policy for fine-grained control
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false

  # Ensure this is applied before the bucket policy
  lifecycle {
    create_before_destroy = true
  }
}

# Enable static website hosting with root redirect
resource "aws_s3_bucket_website_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }

  routing_rules = jsonencode([
    {
      Condition = {
        KeyPrefixEquals = ""
        HttpErrorCodeReturnedEquals = "404"
      }
      Redirect = {
        HostName = "speck.sh"
        Protocol = "https"
        ReplaceKeyWith = ""
      }
    }
  ])
}

# CORS configuration
resource "aws_s3_bucket_cors_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["https://speck.sh", "https://assets.speck.sh"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Bucket policy for public read access
resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id
  depends_on = [aws_s3_bucket_public_access_block.assets]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontGetObject"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.assets.iam_arn
        }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.assets.arn}/*"
      }
    ]
  })
}

# Output the website endpoint
output "assets_bucket_website_endpoint" {
  value = aws_s3_bucket_website_configuration.assets.website_endpoint
}

output "assets_bucket_domain" {
  value = aws_s3_bucket.assets.bucket_regional_domain_name
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

# CloudFront distribution for assets
resource "aws_cloudfront_distribution" "assets_distribution" {
  origin {
    domain_name = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id   = "S3-assets.speck.sh"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.assets.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"  # North America and Europe only (cheapest)
  aliases             = ["assets.speck.sh"]

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-assets.speck.sh"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.assets.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# Create origin access identity for CloudFront to access S3
resource "aws_cloudfront_origin_access_identity" "assets" {
  comment = "access-identity-assets.speck.sh"
}

# Create ACM certificate in us-east-1 (required for CloudFront)
resource "aws_acm_certificate" "assets" {
  provider                  = aws.us_east_1
  domain_name               = "assets.speck.sh"
  validation_method         = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
}

# Output ACM validation details for DNS configuration
output "acm_validation_records" {
  value = {
    for dvo in aws_acm_certificate.assets.domain_validation_options : dvo.domain_name => {
      name    = dvo.resource_record_name
      type    = dvo.resource_record_type
      value   = dvo.resource_record_value
    }
  }
  description = "The DNS records needed to validate the ACM certificate"
}

# Output the CloudFront domain name to use for CNAME
output "cloudfront_domain_for_cname" {
  value = aws_cloudfront_distribution.assets_distribution.domain_name
  description = "Use this CloudFront domain as your CNAME value for assets.speck.sh"
}