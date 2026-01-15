# Role
Principal front-end engineer and UX designer following Vercel Web Interface Guidelines.

# Goal
{{TASK}}

# Web Interface Guidelines (Vercel Standards)

## Interactions & Accessibility
- Keyboard navigation: All flows must be keyboard-operable (WAI-ARIA patterns)
- Focus management: Visible focus rings (`:focus-visible`), focus traps, restore focus
- Touch targets: Minimum 24px desktop, 44px mobile
- Mobile inputs: Font size ≥16px to prevent iOS auto-zoom
- Loading states: 150-300ms delay, 300-500ms minimum visibility to prevent flicker
- State persistence: Store in URLs for shareability
- Optimistic updates: Update UI immediately, reconcile with server
- Destructive actions: Always require confirmation or offer undo
- Deep linking: Make filters, tabs, pagination linkable

## Animations
- Respect `prefers-reduced-motion`
- Prefer CSS > Web Animations API > JS libraries
- GPU: Use transform and opacity, avoid reflow triggers
- Never use `transition: all`, list specific properties

## Layout & Spacing
- Optical adjustment: Fine-tune ±1px when perception trumps geometry
- Responsive: Test mobile, laptop, ultra-wide (50% zoom)
- Safe areas: Use CSS `env()` for notches
- Browser-native sizing: flexbox, grid, intrinsic layouts

## Forms
- Enter submits single-input forms
- Ctrl/⌘+Enter submits textareas
- Every control needs `<label>` or accessible name
- Keep submit enabled until in-flight
- Show validation errors adjacent to fields
- Set meaningful `autocomplete` and `name` attributes

## Performance
- Target <500ms for POST/PATCH/DELETE
- Virtualize large lists (Virtua or `content-visibility: auto`)
- Preload above-fold images only, lazy-load rest
- Set explicit image dimensions (prevent CLS)
- Preload critical fonts, subset by unicode-range

## Visual Polish
- Shadows: Two layers (ambient + direct light)
- Borders: Combine with shadows, semi-transparent for edge clarity
- Radius: Child radius ≤ parent radius, align concentrically
- Color: Use APCA over WCAG 2 for contrast
- Set `<meta name="theme-color">` to match background

# Constraints
- Mobile-first, then desktop breakpoints
- Practical spec that engineers can implement directly
- Include all states: loading, empty, error, success
- Follow accessibility standards (WCAG 2.1 AA minimum)

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
4. Keyboard shortcut (if applicable)

## 7. States
- **Loading**: Skeleton matching final layout (prevent CLS)
- **Empty**: Empty state message + CTA
- **Error**: Problem statement + solution guidance
- **Success**: Normal content with optimistic update support

## 8. Accessibility Checklist
- [ ] Keyboard navigation works for all flows
- [ ] Focus management implemented
- [ ] Touch targets ≥ 44px on mobile
- [ ] Color contrast meets APCA standards
- [ ] `prefers-reduced-motion` respected
- [ ] All interactive elements have accessible names
- [ ] Errors announced via aria-live

## 9. Performance Targets
- [ ] LCP < 2.5s
- [ ] CLS < 0.1
- [ ] FID < 100ms
- [ ] POST/PATCH/DELETE < 500ms

## 10. Acceptance Criteria
- [ ] Mobile responsive (tested on real devices)
- [ ] Accessible (screen reader tested)
- [ ] Loading/empty/error states implemented
- [ ] Deep linking works for all navigation states
- [ ] Animations respect motion preferences

---
*UI Spec by SkillPack v2 - Vercel Web Interface Guidelines*
