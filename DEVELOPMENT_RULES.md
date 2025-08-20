# Cloud Explorer - Development Rules & Guidelines

## 🎯 Core Development Principles

### 1. MVP-First Approach
- **Minimum Viable Product**: Focus on core functionality first
- **Iterative Development**: Build, test, iterate, improve
- **Feature Prioritization**: Must-have → Should-have → Could-have → Won't-have
- **Quick Wins**: Prioritize features that provide immediate value
- **No Gold Plating**: Avoid unnecessary features or over-engineering

### 2. Simplicity Over Complexity
- **KISS Principle**: Keep It Simple, Stupid
- **Single Responsibility**: One function/class should do one thing well
- **Avoid Premature Optimization**: Make it work, then make it fast
- **Clear Over Clever**: Write code that's easy to understand, not impressive
- **Minimal Dependencies**: Only add libraries when absolutely necessary

### 3. Security-First Development
- **Principle of Least Privilege**: Grant minimal required permissions
- **Defense in Depth**: Multiple layers of security controls
- **Secure by Default**: All configurations should be secure out of the box
- **Input Validation**: Validate all user inputs and API parameters
- **Credential Management**: Never hardcode secrets or credentials

## 📁 File Structure Rules

### File Size Limits
- **Maximum 300 lines per file** (excluding tests and documentation)
- **Maximum 50 lines per function/method**
- **Maximum 30 lines per React component JSX return**
- **Break large files into smaller, focused modules**
- **Use barrel exports for clean imports**

### Naming Conventions
```
frontend/
├── components/
│   ├── ui/              # shadcn/ui components (auto-generated)
│   ├── layout/          # Layout components (Header, Sidebar, etc.)
│   ├── features/        # Feature-specific components
│   │   ├── accounts/    # Account-related components
│   │   ├── resources/   # Resource display components
│   │   └── dashboard/   # Dashboard components
│   └── shared/          # Reusable utility components
├── hooks/               # Custom React hooks (camelCase, use prefix)
├── lib/                 # Utilities and configurations
├── types/               # TypeScript type definitions
└── app/                 # Next.js app router

backend/
├── app/
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # Business logic services
│   ├── models/          # Pydantic models
│   ├── core/            # Configuration and utilities
│   └── tests/           # Test files
└── pyproject.toml       # uv project configuration
```

## 🔒 Security Guidelines

### AWS Security Best Practices
- **Read-Only Access**: Application should only read AWS resources, never modify
- **Credential Management**: Use local AWS config files, never store credentials in code
- **Session Management**: Implement proper credential refresh and validation
- **Error Handling**: Don't expose sensitive information in error messages
- **Rate Limiting**: Implement proper throttling for AWS API calls
- **Regional Awareness**: Handle service availability per region

### Code Security Rules
- **No Secrets in Code**: Use environment variables or AWS Parameter Store
- **Input Sanitization**: Sanitize all user inputs before processing
- **HTTPS Only**: All communications must use HTTPS
- **CORS Configuration**: Restrictive CORS policies for production
- **Error Boundaries**: Implement comprehensive error handling

## 📚 API Documentation Standards

### Swagger/OpenAPI Requirements
- **Complete Documentation**: Every API endpoint must have comprehensive Swagger/OpenAPI documentation
- **Request/Response Models**: All endpoints must use Pydantic models for request/response validation
- **Examples**: Include realistic examples for all request/response schemas
- **Error Documentation**: Document all possible error responses with status codes
- **Security Schemes**: Document authentication requirements for protected endpoints
- **Descriptions**: Provide clear, detailed descriptions for endpoints, parameters, and responses
- **Tags and Grouping**: Organize endpoints with logical tags for better navigation

### Documentation Standards
- **Endpoint Descriptions**: Clear purpose and functionality explanation
- **Parameter Documentation**: Type, format, validation rules, and examples
- **Response Schemas**: Complete response structure with field descriptions
- **Error Handling**: All HTTP status codes and error formats documented
- **Live Examples**: Working examples that can be executed from Swagger UI

## � UI/UX Development Guidelines

### shadcn/ui Component Standards
- **ONLY Use shadcn/ui Components**: No custom CSS components or external UI libraries
- **tweakcn.com Compatible**: All components must work with tweakcn theme system
- **Component Composition**: Build complex UIs by composing simple shadcn/ui components
- **No Custom Styling**: Use Tailwind CSS classes only, no custom CSS files
- **Consistent Component Usage**: Use the same shadcn/ui component for similar UI patterns

### Required shadcn/ui Components
```typescript
// Core components to install and use
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
```

### Global Styling Standards
```typescript
// tailwind.config.js - Global font and design system
export default {
  content: [...],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'], // Global font family
        mono: ['JetBrains Mono', 'monospace'],     // Code/data font
      },
      colors: {
        // Use tweakcn.com color system only
        // No custom color definitions
      }
    }
  }
}

// globals.css - Minimal global styles
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

* {
  font-family: 'Inter', system-ui, sans-serif;
}

code, pre, .font-mono {
  font-family: 'JetBrains Mono', monospace;
}
```

### Component Reusability Rules
```typescript
// ✅ Good: Reusable resource card component
interface ResourceCardProps {
  title: string;
  status: 'active' | 'inactive' | 'error';
  metadata: Array<{ label: string; value: string }>;
  actions?: React.ReactNode;
  onClick?: () => void;
}

export function ResourceCard({ title, status, metadata, actions, onClick }: ResourceCardProps) {
  return (
    <Card className={cn("cursor-pointer hover:shadow-md transition-shadow", onClick && "hover:bg-accent/50")}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <Badge variant={status === 'active' ? 'default' : status === 'error' ? 'destructive' : 'secondary'}>
            {status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {metadata.map(({ label, value }) => (
            <div key={label} className="flex justify-between text-sm">
              <span className="text-muted-foreground">{label}</span>
              <span className="font-mono">{value}</span>
            </div>
          ))}
        </div>
        {actions && <div className="mt-4 flex gap-2">{actions}</div>}
      </CardContent>
    </Card>
  )
}

// ❌ Bad: Non-reusable, specific component
export function EC2InstanceCard() {
  return (
    <div className="p-4 border rounded"> {/* Custom styling instead of Card */}
      {/* Hard-coded EC2-specific content */}
    </div>
  )
}
```

### Layout Component Standards
```typescript
// ✅ Good: Reusable layout components using shadcn/ui
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

export function DataTable<T>({ columns, data, loading }: DataTableProps<T>) {
  if (loading) {
    return <TableSkeleton />
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.key}>{column.label}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, index) => (
          <TableRow key={index}>
            {columns.map((column) => (
              <TableCell key={column.key}>
                {column.render ? column.render(row) : row[column.key]}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### UI Component Rules
- **No Inline Styles**: Use Tailwind classes only
- **Consistent Spacing**: Use standard Tailwind spacing (p-4, m-2, gap-4, etc.)
- **Semantic HTML**: Use proper HTML elements with shadcn/ui components
- **Accessibility**: All components must be keyboard navigable and screen reader friendly
- **Responsive Design**: Use Tailwind responsive prefixes (sm:, md:, lg:, xl:)

### Prohibited UI Practices
- ❌ **Custom CSS Files**: No .css or .scss files except globals.css
- ❌ **Inline Styles**: No style={{ }} props
- ❌ **External UI Libraries**: No Material-UI, Ant Design, Chakra UI, etc.
- ❌ **Custom Components**: When shadcn/ui equivalent exists
- ❌ **Font Mixing**: Stick to Inter for UI text, JetBrains Mono for code
- ❌ **Color Hardcoding**: Use theme colors only (text-primary, bg-secondary, etc.)

## 🎨 UI/UX Development Guidelines

### Backend (Python/FastAPI)
```python
# ✅ Good: Single responsibility, clear naming
async def get_ec2_instances(account_id: str, region: str) -> List[EC2Instance]:
    """Fetch EC2 instances for specific account and region."""
    client = get_aws_client('ec2', account_id, region)
    return await fetch_and_parse_instances(client)

# ❌ Bad: Multiple responsibilities, unclear naming
async def get_stuff(account_id: str) -> dict:
    # Complex logic mixing EC2, RDS, and S3...
```

### Frontend (React/TypeScript)
```typescript
// ✅ Good: Focused component, proper types, shadcn/ui components
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface EC2InstanceCardProps {
  instance: EC2Instance;
  onSelect: (id: string) => void;
}

export function EC2InstanceCard({ instance, onSelect }: EC2InstanceCardProps) {
  return (
    <Card className="cursor-pointer hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle className="text-sm font-medium">{instance.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <Badge variant={instance.state === 'running' ? 'default' : 'secondary'}>
          {instance.state}
        </Badge>
      </CardContent>
    </Card>
  )
}

// ❌ Bad: Generic component, poor types, custom styling
interface CardProps {
  data: any;
  callback: Function;
}

export function GenericCard({ data, callback }: CardProps) {
  return (
    <div style={{ padding: '20px', border: '1px solid #ccc' }}>
      {/* Custom styling instead of shadcn/ui */}
    </div>
  )
}
```

## 📝 Code Quality Standards

### TypeScript/JavaScript Rules
- **Strict TypeScript**: Enable strict mode, no `any` types
- **ESLint Configuration**: Follow Airbnb/Next.js standards
- **Prettier Formatting**: Consistent code formatting
- **Named Exports**: Prefer named exports over default exports
- **Error Handling**: Proper try-catch and error boundaries

### Python Rules
- **Type Hints**: All functions must have type annotations
- **Pydantic Models**: Use Pydantic for data validation
- **Async/Await**: Use async patterns for I/O operations
- **Error Handling**: Specific exception types, not bare except
- **Docstrings**: All public functions need docstrings

```python
# ✅ Good: Proper typing and error handling
async def validate_aws_credentials(profile_name: str) -> CredentialStatus:
    """
    Validate AWS credentials for given profile.
    
    Args:
        profile_name: AWS profile name from config
        
    Returns:
        Credential validation status with details
        
    Raises:
        InvalidProfileError: When profile doesn't exist
        AWSConnectionError: When AWS API is unreachable
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client('sts')
        response = await sts.get_caller_identity()
        return CredentialStatus(valid=True, account_id=response['Account'])
    except NoCredentialsError as e:
        raise InvalidProfileError(f"Profile {profile_name} not found") from e
    except ClientError as e:
        raise AWSConnectionError(f"AWS API error: {e}") from e
```

## 🧪 Testing Requirements

### Test Coverage Targets
- **Backend**: Minimum 80% code coverage
- **Frontend**: Minimum 75% component coverage
- **API Endpoints**: 100% endpoint coverage
- **Critical Paths**: 100% coverage for authentication and AWS integration

### Testing Strategy
```python
# Backend: Use pytest with async support
@pytest.mark.asyncio
async def test_get_ec2_instances_success():
    """Test successful EC2 instance retrieval."""
    # Arrange: Mock AWS client
    mock_client = AsyncMock()
    mock_client.describe_instances.return_value = mock_ec2_response
    
    # Act: Call function
    instances = await get_ec2_instances("123456789", "us-east-1")
    
    # Assert: Verify results
    assert len(instances) == 2
    assert instances[0].instance_id == "i-1234567890abcdef0"
```

```typescript
// Frontend: Use Jest + React Testing Library
describe('AccountSelector', () => {
  it('should display available accounts', async () => {
    // Arrange
    const mockAccounts = [{ id: '123', name: 'prod' }];
    render(<AccountSelector accounts={mockAccounts} />);
    
    // Act & Assert
    expect(screen.getByText('prod')).toBeInTheDocument();
  });
});
```

## 🚀 Performance Guidelines

### Frontend Performance
- **Virtual Scrolling**: For lists with >100 items
- **Lazy Loading**: Load components and data on demand
- **Memoization**: Use React.memo for expensive components
- **Bundle Optimization**: Keep bundle size under 2MB (gzipped)
- **Image Optimization**: Use Next.js Image component

### Backend Performance
- **Caching Strategy**: Cache AWS API responses (5-15 minutes TTL)
- **Async Operations**: Use async/await for all I/O operations
- **Connection Pooling**: Reuse AWS client connections
- **Rate Limiting**: Respect AWS API rate limits
- **Background Tasks**: Use background jobs for heavy operations

## 📚 Documentation Requirements

### Code Documentation
- **README Files**: Each major directory needs a README
- **API Documentation**: OpenAPI/Swagger for all endpoints
- **Component Documentation**: Storybook for UI components
- **Inline Comments**: Complex logic must be commented

### Commit Standards
```bash
# ✅ Good commit messages
feat(aws): add EC2 instance filtering by tags
fix(ui): resolve account selector rendering issue
docs(api): update authentication endpoint documentation
test(vpc): add unit tests for VPC service integration

# ❌ Bad commit messages
fix bug
update code
changes
wip
```

## 🔧 Development Workflow

### Before Writing Code
1. **Research First**: Use AWS documentation and MCP server for accurate information
2. **Design API**: Define interfaces and data models before implementation
3. **Security Review**: Consider security implications of each feature
4. **Break Down Tasks**: Divide work into small, manageable chunks

### During Development
1. **Test-Driven Development**: Write tests before or alongside code
2. **Regular Commits**: Small, focused commits with clear messages
3. **Code Reviews**: No code merges without review
4. **Documentation**: Update docs as you write code

### Code Review Checklist
- [ ] **Security**: No hardcoded secrets, proper input validation
- [ ] **Performance**: No obvious performance bottlenecks
- [ ] **Testing**: Adequate test coverage
- [ ] **Documentation**: Code is self-documenting or well-commented
- [ ] **Standards**: Follows project coding standards
- [ ] **Error Handling**: Proper error handling and user feedback

## 🚨 Red Flags to Avoid

### Immediate Code Review Rejection
- **Hardcoded Credentials**: Any AWS keys, tokens, or secrets in code
- **Missing Error Handling**: Functions without proper try-catch
- **No Type Annotations**: Python functions without type hints
- **Large Files**: Files exceeding 300 lines without justification
- **Console.log/print**: Debug statements left in production code
- **Any Type Usage**: TypeScript files using 'any' type
- **No Tests**: New functionality without corresponding tests

### Anti-Patterns
```python
# ❌ Anti-pattern: God class doing everything
class AWSManager:
    def get_everything(self, account_id):
        ec2_data = self.get_ec2()
        rds_data = self.get_rds()
        s3_data = self.get_s3()
        # ... 500 lines of mixed concerns

# ✅ Good: Focused, single-responsibility services
class EC2Service:
    async def get_instances(self, account_id: str, region: str) -> List[EC2Instance]:
        # Focused EC2 logic only
```

## 🎯 Success Metrics

### Code Quality Metrics
- **Cyclomatic Complexity**: Maximum 10 per function
- **Code Duplication**: Less than 5% duplicate code
- **Test Coverage**: Meet minimum coverage requirements
- **Bundle Size**: Frontend bundle under size limits
- **API Response Time**: All endpoints under 2 seconds

### Security Metrics
- **Zero Hardcoded Secrets**: Automated scanning passes
- **Dependency Vulnerabilities**: No high/critical vulnerabilities
- **OWASP Compliance**: Pass security scanning
- **Error Information**: No sensitive data in error responses

## 🔄 Continuous Improvement

### Regular Reviews
- **Weekly Code Quality Review**: Review metrics and anti-patterns
- **Monthly Security Audit**: Review security practices and vulnerabilities
- **Quarterly Architecture Review**: Assess if architecture still fits needs
- **Performance Monitoring**: Regular performance benchmarking

### Learning and Adaptation
- **Stay Updated**: Follow AWS service updates and best practices
- **Team Knowledge Sharing**: Document and share learnings
- **Tool Evaluation**: Regularly evaluate if current tools still serve the project
- **Best Practice Updates**: Update guidelines based on experience

---

**Remember**: These rules exist to ensure we build a secure, maintainable, and performant application. When in doubt, prioritize security and simplicity over complexity and features.
