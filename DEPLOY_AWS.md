# Deploying to AWS

The app needs to start throwaway Docker containers (the sandbox), so the simplest correct
target is **one EC2 instance running Docker**. Total time: ~10 minutes.

## Option A — EC2 + Docker Compose (recommended)

1. **Launch an instance** (EC2 console → Launch instance)
   - AMI: **Amazon Linux 2023**, type: **t3.small** (2 GB RAM; FAISS + Docker need headroom)
   - Key pair: create/select one
   - Security group: allow **SSH (22)** from *your IP only* and **HTTP (80)** from anywhere
   - Advanced details → **User data**: paste [`deploy/aws-ec2-userdata.sh`](deploy/aws-ec2-userdata.sh) (set `REPO_URL` first)
2. **SSH in** and configure secrets:
   ```bash
   ssh -i key.pem ec2-user@<public-ip>
   sudo nano /opt/graph-rag/.env      # set OPENAI_API_KEY, and ACCESS_KEY to a long random string
   ```
3. **Start it:**
   ```bash
   cd /opt/graph-rag && sudo docker compose up -d --build
   ```
4. Open `http://<public-ip>/`. The header pill should read **sandbox: docker**.
   Click and enter your `ACCESS_KEY` once.

Update later with `git pull && sudo docker compose up -d --build`.

### Make it nicer (optional)
- **Elastic IP** so the address survives restarts.
- **HTTPS**: put a free ACM certificate on an Application Load Balancer (target group → port 80,
  health check path `/api/v1/health`) or run Caddy on the instance for automatic Let's Encrypt.
- Store the key in **SSM Parameter Store / Secrets Manager** instead of `.env` for production.

## Option B — ECS Fargate / App Runner (no Docker sandbox)

Fargate and App Runner cannot run Docker-in-Docker, so generated code cannot be sandboxed there.
Set `SANDBOX_FALLBACK=disabled` and the app will refuse to execute code (verification fails
closed). Use Option A unless you replace the sandbox with e.g. AWS Lambda or Firecracker.

## Security checklist
- [x] `ACCESS_KEY` set (otherwise anyone can spend your OpenAI credits)
- [x] `RATE_LIMIT_PER_MIN` set
- [x] SSH restricted to your IP; no other ports open
- [x] Sandbox containers: no network, 128 MB RAM, 0.5 CPU, 64 pids, read-only FS, no capabilities
- [ ] Set an OpenAI **monthly spend limit** in the OpenAI dashboard
