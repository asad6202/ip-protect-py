# IP Protect Frontend

A modern React frontend for the IP Protect Quote Generator system, built with TypeScript, Vite, and shadcn/ui.

## Features

- **Dashboard**: Overview of brands, products, quotes, and uploads
- **Brand Management**: CRUD operations for product brands
- **Product Uploads**: CSV file upload with drag & drop support
- **Product Catalog**: Browse and search products with advanced filtering
- **Quote Generation**: AI-powered quote generation from natural language prompts
- **Quote Management**: Create, edit, view, and manage quotes
- **Rule Engine**: Configure custom rules for quote generation
- **Feedback System**: Collect and manage customer feedback
- **Audit Trail**: Track all prompt runs and quote generation history

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router v6** for routing
- **@tanstack/react-query** for data fetching and caching
- **Axios** for HTTP requests
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **react-hook-form** + **zod** for forms and validation
- **react-dropzone** for file uploads
- **date-fns** for date formatting

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create environment file:
   ```bash
   cp .env.example .env
   ```

4. Update the API base URL in `.env`:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # shadcn/ui components
│   │   └── common/         # Custom common components
│   ├── features/           # Feature-based modules
│   │   ├── brands/         # Brand management
│   │   ├── uploads/        # File upload functionality
│   │   ├── products/       # Product catalog
│   │   ├── quotes/         # Quote generation and management
│   │   ├── rules/          # Rule engine
│   │   ├── feedback/       # Feedback system
│   │   └── prompts/        # Prompt runs audit
│   ├── lib/                # Utilities and configurations
│   │   ├── api.ts          # Axios configuration
│   │   ├── types.ts        # TypeScript type definitions
│   │   ├── format.ts       # Formatting utilities
│   │   └── utils.ts        # General utilities
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # App entry point
│   └── routes.tsx          # Route configuration
├── public/                 # Static assets
├── index.html              # HTML template
├── package.json            # Dependencies and scripts
├── tailwind.config.ts      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── vite.config.ts          # Vite configuration
```

## API Integration

The frontend is designed to work with the FastAPI backend. All API calls are centralized in the `lib/api.ts` file and feature-specific API hooks are located in each feature's `api.ts` file.

### Environment Variables

- `VITE_API_BASE_URL`: Base URL for the API (default: http://localhost:8000)

## Key Features

### Quote Generation Flow

1. **Prompt Entry**: Users enter their requirements in natural language
2. **AI Processing**: The system generates quote items based on the prompt
3. **Review & Edit**: Users can review and modify the generated items
4. **Save Quote**: The quote is saved and can be managed like any other quote

### Rule Engine

- **Rule Sets**: Organize rules into logical groups
- **Rule Types**: Global and item-level rules
- **JSON Configuration**: Flexible condition and action definitions
- **Preset Templates**: Common rule configurations for quick setup

### File Upload

- **Drag & Drop**: Intuitive file upload interface
- **Format Support**: CSV, XLS, XLSX files
- **Brand Association**: Optional brand assignment during upload
- **Progress Tracking**: Real-time upload status updates

## Development Guidelines

### Code Organization

- Use feature-based folder structure
- Keep components small and focused
- Use TypeScript for type safety
- Follow React best practices

### Styling

- Use Tailwind CSS classes
- Leverage shadcn/ui components
- Maintain consistent design system
- Use CSS variables for theming

### State Management

- Use React Query for server state
- Use React hooks for local state
- Avoid prop drilling with context when needed

### Error Handling

- Implement proper error boundaries
- Show user-friendly error messages
- Use toast notifications for feedback
- Log errors for debugging

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Write meaningful commit messages
4. Test your changes thoroughly
5. Update documentation as needed

## License

This project is part of the IP Protect system.
