import type { Metadata } from 'next';
import HalalLensApp from '@/components/halal-lens/HalalLensApp';

export const metadata: Metadata = {
  title: 'Halal Lens — Ingredient Scanner | Noor',
  description: 'Scan food product labels to instantly check if ingredients and E-numbers are halal.',
};

export default function HalalLensPage() {
  return <HalalLensApp />;
}
