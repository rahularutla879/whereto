import type { NextConfig } from "next";

// Fail closed before Next can inline accidentally public database credentials.
// Never include variable values in configuration errors.
if (Object.keys(process.env).some(key => /^NEXT_PUBLIC_.*(?:SUPABASE|DATABASE|DB_PASSWORD|DB_USER|DB_HOST)/i.test(key))) {
  throw new Error("Database configuration must stay in the backend private environment.");
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
};

export default nextConfig;
