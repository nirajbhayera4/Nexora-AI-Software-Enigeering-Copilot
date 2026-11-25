
import Navbar from '../components/Navbar';
import Hero from '../sections/Hero';
import HowItWorks from '../sections/HowItWorks';
import Features from '../sections/Features';
import CTA from '../sections/CTA';
import Footer from '../components/Footer';

function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-transparent">
      <Navbar />
      <Hero />
      <HowItWorks />
      <Features/>
      <CTA />
      <Footer />
    </main>
  );
}

export default Home;
