import { cn } from '@/lib-utils/utils'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function Logo({ className }: LogoProps) {
  return (
    <div className={cn("flex items-center", className)}>
      {/* Logo Image Only */}
      <img
        src="https://www.protect-ip.ca/medias/img/logo-protectip-en.png"
        alt="Protect-IP Logo"
        width= '80%'
      />
    </div>
  )
}
