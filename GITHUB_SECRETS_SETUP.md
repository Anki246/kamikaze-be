# GitHub Secrets Setup for Kamikaze AI Deployment

This document outlines the required GitHub secrets for the CI/CD pipeline deployment.

## Required Secrets

### AWS Configuration
```
AWS_ACCESS_KEY_ID       # AWS access key for deployment
AWS_SECRET_ACCESS_KEY   # AWS secret access key
AWS_REGION             # AWS region (default: us-east-1)
```

### EC2 Configuration
```
EC2_HOST               # EC2 instance public IP or hostname
EC2_USER               # EC2 instance username (usually ubuntu or ec2-user)
EC2_SSH_PRIVATE_KEY    # Private SSH key for EC2 access (PEM format)
```

### Database Configuration (Optional - for AWS Secrets Manager)
```
DB_HOST                # RDS endpoint
DB_NAME                # Database name
DB_USER                # Database username
DB_PASSWORD            # Database password
```

## How to Add Secrets

1. Go to your GitHub repository
2. Click on **Settings** tab
3. Click on **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add each secret with the exact name and value

## Verification

You can verify secrets are properly configured by running the deployment workflow manually:

1. Go to **Actions** tab
2. Select **Deploy Kamikaze AI to AWS EC2**
3. Click **Run workflow**
4. Select the branch and environment
5. Click **Run workflow**

## Security Notes

- Never commit secrets to the repository
- Use AWS IAM roles when possible instead of access keys
- Rotate secrets regularly
- Use least privilege principle for AWS permissions

## Required AWS Permissions

The AWS user/role needs the following permissions:
- EC2 access for deployment
- Secrets Manager access (if using AWS secrets)
- CloudWatch logs access (optional)

## Troubleshooting

### Common Issues:
1. **SSH Connection Failed**: Check EC2_SSH_PRIVATE_KEY format and EC2_HOST
2. **AWS Access Denied**: Verify AWS credentials and permissions
3. **Docker Build Failed**: Check Dockerfile and dependencies
4. **Health Check Failed**: Verify application starts correctly

### Debug Steps:
1. Check GitHub Actions logs for specific error messages
2. Verify all required secrets are set
3. Test SSH connection manually
4. Check EC2 security groups allow SSH (port 22) and HTTP (port 8000)
