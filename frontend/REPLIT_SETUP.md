# Replit Setup Guide for IP Protect Frontend

This guide will help you set up the React frontend in Replit.

## 🚀 Quick Setup

### 1. Import to Replit

1. Go to [Replit](https://replit.com)
2. Click "Create Repl"
3. Choose "Import from GitHub" or "Upload folder"
4. Upload the `frontend` folder or connect to your GitHub repo

### 2. Environment Configuration

The project is pre-configured for Replit with these settings:

- **API Base URL**: `https://ip-protect-py.asad.repl.co` (update this to your actual backend URL)
- **Development Port**: 5173
- **Production Port**: 3000
- **Host**: 0.0.0.0 (required for Replit)

### 3. Install Dependencies

Run in the Replit console:
```bash
npm install
```

### 4. Start Development Server

```bash
npm run dev
```

The app will be available at the Replit URL (usually `https://your-repl-name.your-username.repl.co`)

## 🔧 Configuration Files

### `.replit`
- Configures Replit to run `npm run dev` by default
- Sets up deployment for production
- Configures environment variables

### `replit.nix`
- Defines the Nix environment with Node.js 18
- Includes necessary build tools

### `vite.config.ts`
- Updated for Replit compatibility
- Sets host to `0.0.0.0` for external access
- Configures ports for development and preview

## 🌐 Environment Variables

Update the API base URL in `.replit` file:

```toml
[env]
VITE_API_BASE_URL = "https://your-backend-url.repl.co"
```

## 📦 Available Scripts

- `npm run dev` - Start development server (port 5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build (port 3000)
- `npm run serve` - Serve production build
- `npm start` - Start production server

## 🚀 Deployment

### Development Mode
- Runs automatically when you open the Replit
- Access via the Replit web preview
- Hot reload enabled

### Production Mode
- Build the project: `npm run build`
- Serve the build: `npm run serve`
- Access via the Replit web preview

## 🔗 Backend Integration

Make sure your FastAPI backend is running and accessible. Update the `VITE_API_BASE_URL` in the `.replit` file to point to your backend URL.

## 🐛 Troubleshooting

### Port Issues
- Replit automatically handles port forwarding
- If you get port conflicts, check the `.replit` file

### CORS Issues
- Make sure your backend allows CORS from your Replit domain
- Update CORS settings in your FastAPI backend

### Build Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version: should be 18+

## 📁 Project Structure in Replit

```
frontend/
├── .replit              # Replit configuration
├── replit.nix           # Nix environment
├── .replitignore        # Files to ignore
├── package.json         # Dependencies and scripts
├── vite.config.ts       # Vite configuration
├── src/                 # Source code
├── public/              # Static assets
└── dist/                # Production build (generated)
```

## 🎯 Next Steps

1. **Update API URL**: Change `VITE_API_BASE_URL` to your actual backend URL
2. **Test Connection**: Verify the frontend can connect to your backend
3. **Deploy Backend**: Make sure your FastAPI backend is deployed and accessible
4. **Test Features**: Go through all the features to ensure they work correctly

## 🔄 Updates

To update the project:
1. Pull changes from your repository
2. Run `npm install` if dependencies changed
3. Restart the development server

## 📞 Support

If you encounter issues:
1. Check the Replit console for errors
2. Verify your backend is running and accessible
3. Check the network tab in browser dev tools for API calls
4. Ensure all environment variables are set correctly
