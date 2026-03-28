import Nav from '@/components/Nav';
import Hero from '@/components/Hero';
import About from '@/components/About';
import Services from '@/components/Services';
import Footer from '@/components/Footer';
import { Component as GreenGlow } from '@/components/ui/background-components';

export default function Home() {
  return (
    <GreenGlow>
      <Nav />
      <Hero />
      <About />
      <Services />
      <Footer />
    </GreenGlow>
  );
}
