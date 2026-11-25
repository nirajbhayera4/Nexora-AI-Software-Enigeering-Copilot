import { useEffect, useRef, useState } from 'react';

export default function ScrollReveal({ children, delay = 0, className = '' }) {
    const elementRef = useRef(null);
    const [visible, setVisible] = useState(() => (
        typeof window !== 'undefined' && (
            window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
            !('IntersectionObserver' in window)
        )
    ));

    useEffect(() => {
        const element = elementRef.current;
        if (!element) return undefined;

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduceMotion || !('IntersectionObserver' in window)) return undefined;

        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                setVisible(true);
                observer.unobserve(element);
            }
        }, { threshold: 0.08, rootMargin: '0px 0px -32px 0px' });

        observer.observe(element);
        return () => observer.disconnect();
    }, []);

    return (
        <div
            ref={elementRef}
            className={`scroll-reveal ${visible ? 'is-visible' : ''} ${className}`}
            style={{ transitionDelay: `${delay}ms` }}
        >
            {children}
        </div>
    );
}
