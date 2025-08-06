# Chatlog Component Design & Data Flow

## Component Architecture Overview

### Frontend Component Hierarchy
```
ChatlogApp
├── Layout
│   ├── AppHeader
│   │   ├── Logo
│   │   ├── NavigationMenu
│   │   └── UserActions
│   └── AppFooter
└── Router
    ├── HomePage
    │   ├── HeroSection
    │   │   ├── SearchBox
    │   │   └── QuickActions
    │   ├── PopularQA
    │   │   └── QACard[]
    │   └── Statistics
    ├── SearchPage
    │   ├── SearchHeader
    │   │   ├── SearchBox
    │   │   └── FilterToggle
    │   ├── FilterPanel
    │   │   ├── CategoryFilter
    │   │   ├── DateRangeFilter
    │   │   └── AdvisorFilter
    │   ├── SearchResults
    │   │   ├── ResultsHeader
    │   │   ├── QAList
    │   │   │   └── QACard[]
    │   │   └── Pagination
    │   └── SearchSuggestions
    ├── DetailPage
    │   ├── QADetail
    │   │   ├── QuestionSection
    │   │   ├── AnswerSection
    │   │   ├── MetadataPanel
    │   │   └── ContextDialog
    │   └── RelatedQA
    │       └── QACard[]
    └── AdminPage
        ├── AdminTabs
        │   ├── UploadTab
        │   │   ├── FileUploader
        │   │   └── UploadHistory
        │   ├── ManageTab
        │   │   ├── CategoryManager
        │   │   └── QAEditor
        │   └── StatsTab
        │       ├── SystemMetrics
        │       └── DataCharts
        └── AdminSidebar
```

## Core Components Specifications

### 1. SearchBox Component
```typescript
interface SearchBoxProps {
  placeholder?: string;
  defaultValue?: string;
  onSearch: (query: string, filters?: SearchFilters) => void;
  showFilters?: boolean;
  size?: 'small' | 'default' | 'large';
}

interface SearchFilters {
  category?: string[];
  dateRange?: [Date, Date];
  advisor?: string[];
}

const SearchBox: React.FC<SearchBoxProps> = ({
  placeholder = "搜索问题或答案...",
  defaultValue = "",
  onSearch,
  showFilters = true,
  size = "default"
}) => {
  // Auto-complete suggestions
  // Search history
  // Advanced filters integration
  // Keyboard shortcuts (Ctrl+K)
}
```

### 2. QACard Component
```typescript
interface QACardProps {
  qa: QAPair;
  highlight?: string;
  showCategory?: boolean;
  showActions?: boolean;
  onClick?: (qa: QAPair) => void;
  onEdit?: (qa: QAPair) => void;
  onDelete?: (id: number) => void;
}

interface QAPair {
  id: number;
  question: string;
  answer: string;
  category: Category;
  asker?: string;
  advisor?: string;
  confidence: number;
  createdAt: Date;
  updatedAt: Date;
}

const QACard: React.FC<QACardProps> = ({
  qa,
  highlight,
  showCategory = true,
  showActions = false,
  onClick,
  onEdit,
  onDelete
}) => {
  // Question/answer preview (truncated)
  // Category tag with color
  // Metadata (advisor, date)
  // Confidence indicator
  // Actions menu (edit, delete, copy)
  // Click to expand/navigate
}
```

### 3. FileUploader Component
```typescript
interface FileUploaderProps {
  accept: string[];
  maxSize: number;
  multiple?: boolean;
  onUpload: (files: File[]) => Promise<UploadResult>;
  onProgress?: (progress: number) => void;
}

interface UploadResult {
  success: boolean;
  fileId?: string;
  message: string;
  stats?: {
    totalMessages: number;
    extractedQA: number;
    processingTime: number;
  };
}

const FileUploader: React.FC<FileUploaderProps> = ({
  accept = ['.json'],
  maxSize = 50 * 1024 * 1024, // 50MB
  multiple = false,
  onUpload,
  onProgress
}) => {
  // Drag & drop zone
  // File validation
  // Upload progress
  // Error handling
  // Preview uploaded file info
}
```

### 4. FilterPanel Component
```typescript
interface FilterPanelProps {
  filters: SearchFilters;
  categories: Category[];
  advisors: string[];
  onFilterChange: (filters: SearchFilters) => void;
  onReset: () => void;
  collapsed?: boolean;
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  categories,
  advisors,
  onFilterChange,
  onReset,
  collapsed = false
}) => {
  // Category checkboxes with counts
  // Date range picker
  // Advisor multi-select
  // Clear filters button
  // Responsive collapse/expand
}
```

### 5. CategoryManager Component
```typescript
interface CategoryManagerProps {
  categories: Category[];
  onCreateCategory: (category: Omit<Category, 'id'>) => Promise<void>;
  onUpdateCategory: (id: number, updates: Partial<Category>) => Promise<void>;
  onDeleteCategory: (id: number) => Promise<void>;
}

interface Category {
  id: number;
  name: string;
  description?: string;
  color: string;
  qaCount: number;
  createdAt: Date;
}

const CategoryManager: React.FC<CategoryManagerProps> = ({
  categories,
  onCreateCategory,
  onUpdateCategory,
  onDeleteCategory
}) => {
  // Category list with drag reorder
  // Inline editing
  // Color picker
  // QA count statistics
  // Bulk operations
}
```

## Data Flow Architecture

### 1. Application State Management
```typescript
// Global State (React Context + useReducer)
interface AppState {
  // Auth state
  user: User | null;
  
  // Search state
  searchQuery: string;
  searchFilters: SearchFilters;
  searchResults: QAPair[];
  searchLoading: boolean;
  
  // Upload state
  uploadProgress: number;
  processingStatus: ProcessingStatus;
  
  // Admin state
  categories: Category[];
  systemStats: SystemStats;
  
  // UI state
  sidebarCollapsed: boolean;
  currentPage: string;
}

type AppAction = 
  | { type: 'SET_SEARCH_QUERY'; payload: string }
  | { type: 'SET_SEARCH_RESULTS'; payload: QAPair[] }
  | { type: 'SET_UPLOAD_PROGRESS'; payload: number }
  | { type: 'UPDATE_CATEGORIES'; payload: Category[] }
  | { type: 'TOGGLE_SIDEBAR' };
```

### 2. Data Flow Patterns

#### Search Flow
```
[SearchBox Input] 
  → [useSearch Hook] 
  → [API Service Call] 
  → [Backend Search] 
  → [Database Query] 
  → [Response Processing] 
  → [State Update] 
  → [Component Re-render]
  → [Results Display]
```

#### Upload Flow
```
[File Selection] 
  → [FileUploader Validation] 
  → [useUpload Hook] 
  → [FormData Creation] 
  → [API Upload] 
  → [Backend Processing] 
  → [Progress Updates] 
  → [Completion Notification] 
  → [State Refresh]
```

#### Category Management Flow
```
[Admin Action] 
  → [CategoryManager] 
  → [useCategories Hook] 
  → [API Call] 
  → [Optimistic Update] 
  → [Backend Processing] 
  → [Validation] 
  → [State Sync] 
  → [UI Update]
```

### 3. Custom Hooks Design

#### useSearch Hook
```typescript
interface UseSearchReturn {
  results: QAPair[];
  loading: boolean;
  error: string | null;
  totalCount: number;
  currentPage: number;
  search: (query: string, filters?: SearchFilters) => void;
  loadMore: () => void;
  clearResults: () => void;
}

const useSearch = (): UseSearchReturn => {
  // Debounced search
  // Pagination handling
  // Error management
  // Loading states
  // Cache management
}
```

#### useUpload Hook
```typescript
interface UseUploadReturn {
  upload: (files: File[]) => Promise<UploadResult>;
  progress: number;
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  error: string | null;
  cancel: () => void;
}

const useUpload = (): UseUploadReturn => {
  // File upload with progress
  // Upload cancellation
  // Error handling
  // Status tracking
}
```

#### useCategories Hook
```typescript
interface UseCategoriesReturn {
  categories: Category[];
  loading: boolean;
  create: (category: Omit<Category, 'id'>) => Promise<Category>;
  update: (id: number, updates: Partial<Category>) => Promise<Category>;
  delete: (id: number) => Promise<void>;
  refresh: () => void;
}

const useCategories = (): UseCategoriesReturn => {
  // CRUD operations
  // Optimistic updates
  // Cache management
  // Error handling
}
```

## Component Communication Patterns

### 1. Parent-Child Communication
```typescript
// Props down, events up pattern
<SearchPage>
  <SearchBox onSearch={handleSearch} />
  <FilterPanel 
    filters={currentFilters} 
    onFilterChange={handleFilterChange} 
  />
  <SearchResults 
    results={searchResults} 
    onItemClick={handleItemClick} 
  />
</SearchPage>
```

### 2. Sibling Communication via Context
```typescript
// Shared state through context
const SearchContext = createContext<{
  query: string;
  filters: SearchFilters;
  results: QAPair[];
  updateQuery: (query: string) => void;
  updateFilters: (filters: SearchFilters) => void;
}>(null);

// Components subscribe to shared state
const SearchBox = () => {
  const { query, updateQuery } = useContext(SearchContext);
  // ...
}
```

### 3. Event Bus for Cross-Component Communication
```typescript
// Custom event system for loosely coupled components
class EventBus {
  private events: { [key: string]: Function[] } = {};
  
  on(event: string, callback: Function) {
    if (!this.events[event]) this.events[event] = [];
    this.events[event].push(callback);
  }
  
  emit(event: string, data: any) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
}

// Usage
eventBus.emit('qa:updated', updatedQA);
eventBus.on('qa:updated', (qa) => refreshRelatedData());
```

## Performance Optimization

### 1. Component Optimization
```typescript
// Memoization for expensive components
const QACard = React.memo(({ qa, highlight }) => {
  // Component logic
}, (prevProps, nextProps) => {
  return prevProps.qa.id === nextProps.qa.id && 
         prevProps.highlight === nextProps.highlight;
});

// Virtual scrolling for large lists
const VirtualizedQAList = ({ items, itemHeight = 120 }) => {
  return (
    <FixedSizeList
      height={600}
      itemCount={items.length}
      itemSize={itemHeight}
      itemData={items}
    >
      {QACardRow}
    </FixedSizeList>
  );
};
```

### 2. State Optimization
```typescript
// Selective subscriptions
const useQAData = (qaId: number) => {
  return useSelector((state: AppState) => 
    state.qaList.find(qa => qa.id === qaId)
  );
};

// Normalized state structure
interface NormalizedState {
  qa: {
    byId: { [id: number]: QAPair };
    allIds: number[];
  };
  categories: {
    byId: { [id: number]: Category };
    allIds: number[];
  };
}
```

### 3. Loading Strategies
```typescript
// Progressive loading
const SearchResults = () => {
  const [page, setPage] = useState(1);
  const { results, hasMore, loading } = useInfiniteQuery(
    ['search', query, filters, page],
    ({ pageParam = 1 }) => searchAPI.search(query, filters, pageParam),
    {
      getNextPageParam: (lastPage) => lastPage.nextPage,
    }
  );
  
  return (
    <InfiniteScroll
      dataLength={results.length}
      next={() => setPage(page + 1)}
      hasMore={hasMore}
      loader={<Spinner />}
    >
      {results.map(qa => <QACard key={qa.id} qa={qa} />)}
    </InfiniteScroll>
  );
};
```

## Error Handling & User Feedback

### 1. Error Boundaries
```typescript
class QAErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error, errorInfo) {
    console.error('QA Component Error:', error, errorInfo);
    // Send to error reporting service
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

### 2. User Feedback System
```typescript
// Toast notifications for user actions
const useToast = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  const showToast = (message: string, type: 'success' | 'error' | 'warning') => {
    const toast = { id: Date.now(), message, type };
    setToasts(prev => [...prev, toast]);
    setTimeout(() => removeToast(toast.id), 5000);
  };
  
  return { toasts, showToast };
};

// Loading states
const LoadingSpinner = ({ size = 'default', text = '加载中...' }) => (
  <div className={`loading-spinner loading-${size}`}>
    <Spin size={size} />
    <span>{text}</span>
  </div>
);
```

## Accessibility & Internationalization

### 1. Accessibility Features
```typescript
// Keyboard navigation
const SearchBox = () => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
    if (e.key === 'Escape') clearSearch();
    if (e.ctrlKey && e.key === 'k') focusSearch();
  };
  
  return (
    <Input
      placeholder="搜索问题或答案..."
      onKeyDown={handleKeyDown}
      aria-label="搜索知识库"
      role="search"
    />
  );
};

// Screen reader support
const QACard = ({ qa }) => (
  <div 
    role="article" 
    aria-labelledby={`qa-${qa.id}-question`}
    aria-describedby={`qa-${qa.id}-answer`}
  >
    <h3 id={`qa-${qa.id}-question`}>{qa.question}</h3>
    <div id={`qa-${qa.id}-answer`}>{qa.answer}</div>
  </div>
);
```

### 2. Internationalization Structure
```typescript
// i18n configuration
const i18nConfig = {
  'zh-CN': {
    search: {
      placeholder: '搜索问题或答案...',
      noResults: '未找到相关问答',
      suggestions: '搜索建议'
    },
    categories: {
      product: '产品咨询',
      technical: '技术支持',
      pricing: '价格费用'
    }
  },
  'en-US': {
    search: {
      placeholder: 'Search questions or answers...',
      noResults: 'No QA found',
      suggestions: 'Search suggestions'
    }
  }
};

const useI18n = () => {
  const [locale, setLocale] = useState('zh-CN');
  const t = (key: string) => get(i18nConfig[locale], key, key);
  return { t, locale, setLocale };
};
```