# Development Checklist - Quick Reference

## 🔥 Before You Code (STOP & THINK)
- [ ] Did I research this feature using AWS documentation first?
- [ ] Is this the simplest approach that meets the requirement?
- [ ] Does this follow the MVP principle (no over-engineering)?
- [ ] Have I considered security implications?
- [ ] Is the file I'm about to edit under 300 lines?

## ✅ Code Quality Checklist

### Every Function/Component
- [ ] **Single Responsibility**: Does one thing well
- [ ] **Proper Naming**: Clear, descriptive names
- [ ] **Type Safety**: TypeScript types or Python type hints
- [ ] **Error Handling**: Proper try-catch and error boundaries
- [ ] **Documentation**: Docstring/comments for complex logic
- [ ] **Under 50 Lines**: Break down if longer

### Security Checklist
- [ ] **No Hardcoded Secrets**: Check for AWS keys, tokens, passwords
- [ ] **Input Validation**: All user inputs validated and sanitized
- [ ] **Least Privilege**: AWS permissions are minimal
- [ ] **HTTPS Only**: All network communication is secure
- [ ] **Error Messages**: No sensitive data exposed in errors

### Performance Checklist
- [ ] **Async Operations**: I/O operations use async/await
- [ ] **Caching**: AWS API responses are cached appropriately
- [ ] **Virtual Scrolling**: Lists >100 items use virtual scrolling
- [ ] **Lazy Loading**: Components/data loaded on demand
- [ ] **Rate Limiting**: AWS API calls respect rate limits

## 🧪 Testing Requirements
- [ ] **Unit Tests**: New functions have unit tests
- [ ] **Integration Tests**: API endpoints have integration tests
- [ ] **Error Cases**: Test error conditions and edge cases
- [ ] **Coverage**: Meets minimum coverage requirements
- [ ] **Mock AWS**: Tests use mocked AWS responses

## 📝 Before Commit
- [ ] **Lint Passes**: ESLint/Pylint with no errors
- [ ] **Tests Pass**: All tests passing locally
- [ ] **No Debug Code**: Remove console.log/print statements
- [ ] **Proper Commit Message**: Follow conventional commits
- [ ] **Documentation Updated**: README/docs reflect changes

## 🚨 Red Flags (Automatic Rejection)
- ❌ Hardcoded AWS credentials or secrets
- ❌ Files over 300 lines without justification
- ❌ Functions over 50 lines without breakdown
- ❌ React component JSX over 30 lines without breakdown
- ❌ Missing error handling
- ❌ TypeScript 'any' types
- ❌ Python functions without type hints
- ❌ New code without tests
- ❌ Debug statements in production code
- ❌ Custom CSS files or inline styles
- ❌ Non-shadcn/ui components when shadcn/ui equivalent exists
- ❌ Hardcoded colors or fonts
- ❌ External UI libraries (Material-UI, Ant Design, etc.)

## 🎯 AWS Integration Guidelines
- [ ] **Read-Only Access**: Never modify AWS resources
- [ ] **Regional Handling**: Account for service regional availability
- [ ] **Credential Refresh**: Handle credential expiration
- [ ] **Service Limits**: Respect AWS service quotas
- [ ] **Error Mapping**: Map AWS errors to user-friendly messages

## 📱 UI/UX Standards
- [ ] **shadcn/ui Only**: Using only shadcn/ui components, no external UI libraries
- [ ] **tweakcn Compatible**: Components work with tweakcn theme system
- [ ] **Reusable Components**: Creating composable, reusable components
- [ ] **Global Font Family**: Using Inter for UI, JetBrains Mono for code/data
- [ ] **No Custom CSS**: Using Tailwind classes only, no custom stylesheets
- [ ] **Consistent Spacing**: Using standard Tailwind spacing classes
- [ ] **Component Composition**: Building complex UIs from simple shadcn/ui components
- [ ] **Responsive Design**: Works on mobile and desktop with Tailwind responsive classes
- [ ] **Loading States**: Show Skeleton components during loading
- [ ] **Error States**: Display user-friendly error messages with Alert components
- [ ] **Accessibility**: WCAG 2.1 AA compliance with proper ARIA labels
- [ ] **Performance**: Under 3-second load times
- [ ] **Theme Colors**: Using theme color classes, no hardcoded colors

## 🔄 Daily Development Habits
1. **Start with Research**: Check AWS docs before coding
2. **Security First**: Consider security implications
3. **Test Early**: Write tests alongside code
4. **Document as You Go**: Update docs with changes
5. **Review Your Own Code**: Self-review before committing

---
**Keep this checklist open while coding - it's your safety net! 🛡️**
