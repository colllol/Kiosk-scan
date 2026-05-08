const fs = require('fs');
const { createCanvas } = require('canvas');

function createIcon(size, outputPath) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');
  
  // Background with rounded corners
  ctx.fillStyle = '#2196f3';
  ctx.beginPath();
  const radius = size * 0.15;
  ctx.roundRect(0, 0, size, size, radius);
  ctx.fill();
  
  // Form icon lines
  ctx.fillStyle = 'white';
  const padding = size * 0.2;
  const lineHeight = size * 0.08;
  const gap = size * 0.15;
  
  ctx.fillRect(padding, padding, size - padding * 2, lineHeight);
  ctx.fillRect(padding, padding + gap, size - padding * 2, lineHeight);
  ctx.fillRect(padding, padding + gap * 2, (size - padding * 2) * 0.6, lineHeight);
  
  // AF text
  ctx.font = `bold ${size * 0.2}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('AF', size / 2, size * 0.72);
  
  // Save to file
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(outputPath, buffer);
  console.log(`Created ${outputPath} (${size}x${size})`);
}

// Create all icon sizes
const iconsDir = './icons';
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

createIcon(16, `${iconsDir}/icon16.png`);
createIcon(48, `${iconsDir}/icon48.png`);
createIcon(128, `${iconsDir}/icon128.png`);

console.log('\nAll icons created successfully!');
console.log('You can now load the extension in Chrome.');
