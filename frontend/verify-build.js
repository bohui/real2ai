#!/usr/bin/env node

/**
 * Build verification script for Cloudflare Pages deployment
 */

const fs = require('fs');
const path = require('path');

const DIST_DIR = './dist';
const REQUIRED_FILES = [
  'index.html',
  '_redirects',
  '_headers',
  'assets',
  'favicon.ico',
  'robots.txt',
  'site.webmanifest'
];

console.log('🔍 Verifying Cloudflare Pages build...\n');

// Check if dist directory exists
if (!fs.existsSync(DIST_DIR)) {
  console.error('❌ dist directory not found. Run npm run build:cloudflare first.');
  process.exit(1);
}

// Check required files
const missingFiles = [];
REQUIRED_FILES.forEach(file => {
  const filePath = path.join(DIST_DIR, file);
  if (!fs.existsSync(filePath)) {
    missingFiles.push(file);
  }
});

if (missingFiles.length > 0) {
  console.error('❌ Missing required files:');
  missingFiles.forEach(file => console.error(`   - ${file}`));
  process.exit(1);
}

// Check _redirects content
const redirectsContent = fs.readFileSync(path.join(DIST_DIR, '_redirects'), 'utf8');
if (!redirectsContent.includes('/*    /index.html   200')) {
  console.error('❌ _redirects file missing SPA fallback rule');
  process.exit(1);
}

// Check _headers content
const headersContent = fs.readFileSync(path.join(DIST_DIR, '_headers'), 'utf8');
if (!headersContent.includes('Cache-Control')) {
  console.error('❌ _headers file missing cache control');
  process.exit(1);
}

// Check index.html content
const indexContent = fs.readFileSync(path.join(DIST_DIR, 'index.html'), 'utf8');
if (!indexContent.includes('crossorigin src="/assets/')) {
  console.error('❌ index.html missing proper asset references');
  process.exit(1);
}

// Check assets directory
const assetsDir = path.join(DIST_DIR, 'assets');
const assets = fs.readdirSync(assetsDir);
const requiredAssets = ['js', 'css'];

requiredAssets.forEach(type => {
  const hasAsset = assets.some(asset => asset.endsWith(`.${type}`));
  if (!hasAsset) {
    console.error(`❌ Missing ${type} assets in assets directory`);
    process.exit(1);
  }
});

// Get build statistics
const stats = {
  totalFiles: 0,
  totalSize: 0,
  jsFiles: 0,
  cssFiles: 0
};

function calculateDirSize(dirPath) {
  const files = fs.readdirSync(dirPath);
  files.forEach(file => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      calculateDirSize(filePath);
    } else {
      stats.totalFiles++;
      stats.totalSize += stat.size;
      if (file.endsWith('.js')) stats.jsFiles++;
      if (file.endsWith('.css')) stats.cssFiles++;
    }
  });
}

calculateDirSize(DIST_DIR);

console.log('✅ All required files present');
console.log('✅ SPA routing configured correctly');
console.log('✅ Cache headers configured');
console.log('✅ Assets properly referenced');
console.log('');
console.log('📊 Build Statistics:');
console.log(`   📁 Total files: ${stats.totalFiles}`);
console.log(`   📦 Total size: ${(stats.totalSize / 1024 / 1024).toFixed(2)} MB`);
console.log(`   🟨 JavaScript files: ${stats.jsFiles}`);
console.log(`   🟦 CSS files: ${stats.cssFiles}`);
console.log('');
console.log('🚀 Build verification passed! Ready for Cloudflare Pages deployment.');
console.log('');
console.log('📋 Next steps:');
console.log('   1. Upload dist/ folder to Cloudflare Pages');
console.log('   2. Configure environment variables');
console.log('   3. Set up custom domain (optional)');
console.log('   4. Update API URLs in _redirects file');