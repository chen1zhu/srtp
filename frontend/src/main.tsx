import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import SimpleAIChat from './SimpleAIChat.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SimpleAIChat />
  </StrictMode>,
)
