import React from 'react';
import './ColorBlock.css';

interface ColorBlockProps {
  color?: 'lime' | 'lilac' | 'cream' | 'pink' | 'mint' | 'coral' | 'navy';
  children: React.ReactNode;
  className?: string;
}

export const ColorBlock: React.FC<ColorBlockProps> = ({ color = 'lime', children, className = '' }) => {
  return (
    <section className={`color-block color-block-${color} ${className}`}>
      {children}
    </section>
  );
};
