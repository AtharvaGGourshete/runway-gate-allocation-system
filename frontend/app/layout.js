import { Inter } from "next/font/google";
import "./globals.css";
import Footer from "@/components/Footer";
// import "mapbox-gl/dist/mapbox-gl.css";
import "leaflet/dist/leaflet.css";


const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata = {
  title: "Skyslot",
  description: "Real-time runway and gate optimizer.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable}`}
      >
        {children}
        <Footer />
      </body>
    </html>
  );
}
