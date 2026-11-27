-- Separate schema for the .NET migration so the existing Python/MySQL schema remains untouched.
CREATE DATABASE IF NOT EXISTS finmarket_dotnet
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
