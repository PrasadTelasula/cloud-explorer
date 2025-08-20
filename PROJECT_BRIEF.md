# Cloud Explorer - Project Brief

## Overview
A web-based application that provides a unified dashboard to view and monitor AWS cloud resources (EC2, RDS, VPC, S3, etc.) across multiple AWS accounts from a single interface. The application will read AWS credentials from local configuration files and present the data in an intuitive, modern UI.

## Tech Stack
- **Frontend**: Next.js with TypeScript, Tailwind CSS, shadcn/ui (tweakcn.com compatible)
- **Backend**: Python FastAPI for AWS resource fetching
- **AWS SDK**: boto3 for AWS service interactions
- **Authentication**: Local AWS config file (~/.aws/config and ~/.aws/credentials)

## Core Features

### 1. Multi-Account Management
- Read AWS profiles from local `~/.aws/config` and `~/.aws/credentials`
- Allow users to select multiple AWS accounts simultaneously
- Display account selection interface with profile names and regions
- Store selected accounts in local state/session

### 2. Resource Discovery
- **EC2 Instances**: Instance ID, type, state, launch time, tags
- **RDS Databases**: DB identifier, engine, status, endpoint
- **VPC Resources**: VPCs, subnets, security groups, route tables
- **S3 Buckets**: Bucket names, creation date, region
- **Lambda Functions**: Function names, runtime, last modified
- **Load Balancers**: ALB/NLB details, target groups, health status

### 3. User Interface
- Clean, responsive dashboard using shadcn/ui components
- Resource cards/tables with filtering and sorting capabilities
- Account switcher component
- Resource type navigation (sidebar or tabs)
- Search functionality across resources
- Export capabilities (CSV/JSON)

### 4. Data Management
- Real-time resource fetching (with caching for performance)
- Error handling for failed AWS API calls
- Loading states and progress indicators
- Refresh functionality for updated data

## Project Structure

```
cloud-explorer/
├── frontend/                 # Next.js application
│   ├── app/                 # App router
│   ├── components/          # shadcn/ui components
│   ├── lib/                # Utilities and configurations
│   └── types/              # TypeScript type definitions
├── backend/                 # Python FastAPI application
│   ├── app/
│   │   ├── routers/        # API route handlers
│   │   ├── services/       # AWS service integrations
│   │   ├── models/         # Pydantic models
│   │   └── core/           # Configuration and utilities
│   ├── requirements.txt
│   └── main.py
└── README.md
```

## Development Phases

### Phase 1: Foundation (Week 1)
- Set up Next.js frontend with shadcn/ui
- Configure Python FastAPI backend
- Implement AWS credential reading from local config
- Create basic account selection interface
- Set up API communication between frontend and backend

### Phase 2: Core Resources (Week 2)
- Implement EC2 instance discovery and display
- Add VPC resource fetching (VPCs, subnets, security groups)
- Create responsive resource cards/tables
- Add basic filtering and sorting

### Phase 3: Extended Resources (Week 3)
- Add RDS database discovery
- Implement S3 bucket listing
- Add Lambda function discovery
- Include Load Balancer information

### Phase 4: Enhancement (Week 4)
- Implement search functionality
- Add export capabilities
- Error handling and loading states
- Performance optimization and caching
- UI polish and responsive design improvements

## Key Components

### Backend APIs
- `GET /api/accounts` - List available AWS profiles
- `GET /api/resources/{account_id}/{resource_type}` - Fetch specific resources
- `GET /api/resources/bulk` - Fetch multiple resource types across accounts
- `POST /api/validate-credentials` - Validate AWS credentials

### Frontend Components
- `AccountSelector` - Multi-select dropdown for AWS accounts
- `ResourceDashboard` - Main dashboard layout
- `ResourceCard` - Individual resource display component
- `ResourceTable` - Tabular view of resources
- `FilterBar` - Search and filter controls
- `NavSidebar` - Resource type navigation

## Security & Best Practices
- Never store AWS credentials in the application
- Read-only access to AWS resources (no modification capabilities)
- Local credential file access only
- Rate limiting for AWS API calls
- Error boundary components for graceful failure handling

## Non-Functional Requirements
- Responsive design (mobile-friendly)
- Fast loading times (<3 seconds for resource lists)
- Support for 10+ AWS accounts simultaneously
- Graceful degradation when AWS services are unavailable
- Minimal dependencies to reduce complexity

## Future Enhancements (Not in MVP)
- Real-time updates via WebSockets
- Cost information integration
- Resource health monitoring
- Custom dashboards and saved views
- Resource tagging and organization
- Integration with other cloud providers (Azure, GCP)

## Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+
- AWS CLI configured with multiple profiles
- Valid AWS credentials in `~/.aws/credentials` and `~/.aws/config`

### Installation Steps
1. Clone the repository
2. Set up the frontend (Next.js)
3. Set up the backend (FastAPI)
4. Configure environment variables
5. Run both services

### Environment Variables
- `AWS_PROFILE_PATH`: Path to AWS credentials (default: ~/.aws/)
- `BACKEND_URL`: FastAPI backend URL for frontend
- `CORS_ORIGINS`: Allowed origins for CORS

## Architecture Notes
This approach keeps the project focused and deliverable while providing a solid foundation for future enhancements. The architecture is simple but scalable, avoiding over-engineering while meeting all core requirements.

The separation of frontend and backend allows for:
- Independent scaling
- Technology-specific optimizations
- Clear separation of concerns
- Easy testing and deployment
