/**
 * Optimized Lazy Loading Image Component
 * Features: WebP support, intersection observer, blur-to-sharp transition
 */

import { useState, useRef, useEffect } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  placeholder?: string;
  blurDataURL?: string;
  sizes?: string;
  priority?: boolean;
  onLoad?: () => void;
  onError?: () => void;
}

export default function LazyImage({
  src,
  alt,
  width,
  height,
  className = '',
  placeholder,
  blurDataURL,
  sizes = '100vw',
  priority = false,
  onLoad,
  onError
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(priority);
  const [hasError, setHasError] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string>(placeholder || blurDataURL || '');
  const imgRef = useRef<HTMLImageElement>(null);

  // Generate WebP and fallback sources
  const generateSources = (originalSrc: string) => {
    const extensions = ['.jpg', '.jpeg', '.png'];
    const hasExtension = extensions.some(ext => originalSrc.toLowerCase().endsWith(ext));
    
    if (!hasExtension) return { webp: originalSrc, fallback: originalSrc };
    
    const webpSrc = extensions.reduce((src, ext) => 
      src.replace(new RegExp(ext + '$', 'i'), '.webp'), originalSrc
    );
    
    return { webp: webpSrc, fallback: originalSrc };
  };

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (priority || isInView) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '50px', // Start loading 50px before visible
        threshold: 0.1
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, [priority, isInView]);

  // Load image when in view
  useEffect(() => {
    if (!isInView || isLoaded) return;

    const { webp, fallback } = generateSources(src);
    
    // Try WebP first, fallback to original
    const testWebP = new Image();
    testWebP.onload = () => {
      setCurrentSrc(webp);
      setIsLoaded(true);
      onLoad?.();
    };
    
    testWebP.onerror = () => {
      // WebP not supported or failed, use original
      const testOriginal = new Image();
      testOriginal.onload = () => {
        setCurrentSrc(fallback);
        setIsLoaded(true);
        onLoad?.();
      };
      
      testOriginal.onerror = () => {
        setHasError(true);
        onError?.();
      };
      
      testOriginal.src = fallback;
    };
    
    testWebP.src = webp;
  }, [isInView, src, isLoaded, onLoad, onError]);

  // Render placeholder or error state
  if (hasError) {
    return (
      <div 
        className={`bg-gray-200 flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
        <span className="text-gray-500 text-sm">Failed to load image</span>
      </div>
    );
  }

  // Render skeleton while loading
  if (!isInView && !priority) {
    return (
      <div 
        ref={imgRef}
        className={`bg-gray-200 animate-pulse ${className}`}
        style={{ width, height }}
        aria-label={`Loading ${alt}`}
      />
    );
  }

  return (
    <div className={`relative overflow-hidden ${className}`} style={{ width, height }}>
      {/* Blur placeholder */}
      {!isLoaded && blurDataURL && (
        <img
          src={blurDataURL}
          alt=""
          className="absolute inset-0 w-full h-full object-cover filter blur-sm scale-110"
          aria-hidden="true"
        />
      )}
      
      {/* Main image */}
      <img
        ref={imgRef}
        src={currentSrc}
        alt={alt}
        width={width}
        height={height}
        sizes={sizes}
        className={`
          w-full h-full object-cover transition-opacity duration-300
          ${isLoaded ? 'opacity-100' : 'opacity-0'}
          ${className}
        `}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        onLoad={() => {
          setIsLoaded(true);
          onLoad?.();
        }}
        onError={() => {
          setHasError(true);
          onError?.();
        }}
      />
      
      {/* Loading indicator */}
      {!isLoaded && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}

/**
 * Utility function to generate blur data URL from image
 */
export function generateBlurDataURL(_src: string, width: number = 40, height: number = 40): string {
  // This is a placeholder implementation
  // In a real app, you might use a service like Cloudinary or similar
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  
  if (ctx) {
    // Create a simple gradient as placeholder
    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, '#f3f4f6');
    gradient.addColorStop(1, '#e5e7eb');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  }
  
  return canvas.toDataURL();
}

/**
 * Hook for preloading critical images
 */
export function useImagePreload(srcs: string[]) {
  useEffect(() => {
    srcs.forEach(src => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = src;
      document.head.appendChild(link);
    });
  }, [srcs]);
}