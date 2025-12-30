# Role
Principal front-end engineer and UX designer.

# Goal
{{TASK}}

# Constraints
- Mobile-first, then desktop breakpoints
- Practical spec that engineers can implement directly
- Include all states: loading, empty, error, success

# Output Format (Markdown)

## 1. High-Level UX
Brief description of the user experience and flow.

## 2. Layout

### Mobile (< 768px)
```
┌─────────────────┐
│     Header      │
├─────────────────┤
│                 │
│   Main Area     │
│                 │
├─────────────────┤
│     Footer      │
└─────────────────┘
```

### Desktop (≥ 1024px)
```
┌────────┬────────────────────┐
│        │                    │
│ Sidebar│    Main Content    │
│        │                    │
└────────┴────────────────────┘
```

## 3. Component Tree
```
<PageName>
├── <Header>
│   └── <NavItems>
├── <MainContent>
│   ├── <ComponentA prop={...}>
│   └── <ComponentB>
│       └── <SubComponent>
└── <Footer>
```

### Component Props
| Component | Props | Type | Required |
|-----------|-------|------|----------|
| ComponentA | data | DataType[] | yes |

## 4. State Model
```typescript
interface PageState {
  isLoading: boolean;
  error: Error | null;
  data: DataType[];
}

type Actions = 
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; payload: DataType[] }
  | { type: 'FETCH_ERROR'; payload: Error };
```

## 5. API/Data Requirements
| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| /api/... | GET | - | DataType[] |

## 6. Interaction Flows

### Flow 1: [Name]
1. User action
2. System response
3. State change

## 7. States
- **Loading**: Skeleton/spinner
- **Empty**: Empty state message + CTA
- **Error**: Error message + retry button
- **Success**: Normal content

## 8. Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Mobile responsive
- [ ] Accessible (ARIA labels)

---
*UI Spec by SkillPack v2*
