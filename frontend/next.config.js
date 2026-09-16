/** @type {import('next').NextConfig} */
const nextConfig = {
  // Hide the floating dev-mode badge; it overlaps page content on small screens.
  // Compile and runtime errors are still shown.
  devIndicators: false,
};

module.exports = nextConfig;
