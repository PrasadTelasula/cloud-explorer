# Cloud Explorer

A web-based application that provides a unified dashboard to view and monitor AWS cloud resources (EC2, RDS, VPC, S3, etc.) across multiple AWS accounts from a single interface.

## 🚀 Features

- **Multi-Account Support**: View resources across multiple AWS accounts simultaneously
- **Resource Discovery**: EC2, VPC, RDS, S3, Lambda, Load Balancers, and more
- **Security-First**: Read-only access, local credential management
- **Modern UI**: Built with Next.js, shadcn/ui, and Tailwind CSS
- **Fast Performance**: Intelligent caching and optimized data fetching

## 🛠️ Tech Stack

- **Frontend**: Next.js 14+, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python FastAPI, boto3, pydantic
- **Package Management**: uv (Python), npm (Node.js)
- **AWS Integration**: boto3 with local credential management

## 📋 Prerequisites

- Node.js 18+
- Python 3.9+
- uv (Python package manager)
- Docker (optional)
- AWS CLI configured with multiple profiles

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd cloud-explorer
```

### 2. Backend Setup
```bash
cd backend
uv init
uv add fastapi uvicorn boto3 python-dotenv pydantic
uv run uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. AWS Configuration
Ensure your `~/.aws/credentials` and `~/.aws/config` files are properly configured with multiple profiles.

## 📚 Documentation

- [Project Brief](./PROJECT_BRIEF.md) - Complete project overview
- [Task List](./TASK_LIST.md) - Development roadmap and progress
- [Development Rules](./DEVELOPMENT_RULES.md) - Coding standards and guidelines
- [Development Checklist](./DEV_CHECKLIST.md) - Quick reference for developers

## 🔒 Security

- **Read-Only Access**: Application only reads AWS resources, never modifies
- **Local Credentials**: Uses local AWS configuration files
- **No Hardcoded Secrets**: All sensitive data handled through environment variables
- **Principle of Least Privilege**: Minimal required AWS permissions

## 📁 Project Structure

```
cloud-explorer/
├── frontend/                 # Next.js application
│   ├── app/                 # App router
│   ├── components/          # React components
│   │   ├── ui/              # shadcn/ui components
│   │   ├── layout/          # Layout components
│   │   ├── features/        # Feature-specific components
│   │   └── shared/          # Reusable components
│   ├── lib/                 # Utilities and configurations
│   └── types/               # TypeScript type definitions
├── backend/                 # Python FastAPI application
│   ├── app/
│   │   ├── routers/         # API route handlers
│   │   ├── services/        # AWS service integrations
│   │   ├── models/          # Pydantic models
│   │   └── core/            # Configuration and utilities
│   └── pyproject.toml       # uv project configuration
└── docs/                    # Documentation
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
uv run pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📦 Deployment

Deployment instructions will be added as the project progresses.

## 🤝 Contributing

1. Read the [Development Rules](./DEVELOPMENT_RULES.md)
2. Check the [Development Checklist](./DEV_CHECKLIST.md)
3. Follow the task list in [TASK_LIST.md](./TASK_LIST.md)
4. Create a feature branch
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This application is designed for monitoring and viewing AWS resources only. It does not perform any modifications to your AWS infrastructure. Always ensure your AWS credentials have appropriate read-only permissions.
