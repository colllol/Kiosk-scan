// Simple icon generator - creates basic PNG icons
// Run this in browser console or use a tool to convert SVG to PNG

function createIcon(size) {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  
  // Background
  ctx.fillStyle = '#2196f3';
  ctx.fillRect(0, 0, size, size);
  
  // Rounded corners
  const radius = size * 0.15;
  ctx.globalCompositeOperation = 'destination-in';
  ctx.beginPath();
  ctx.roundRect(0, 0, size, size, radius);
  ctx.fill();
  ctx.globalCompositeOperation = 'source-over';
  
  // Form icon
  ctx.fillStyle = 'white';
  const padding = size * 0.25;
  const iconSize = size - padding * 2;
  
  // Draw simplified form lines
  ctx.fillRect(padding, padding * 0.8, iconSize, iconSize * 0.1);
  ctx.fillRect(padding, padding * 1.2, iconSize, iconSize * 0.1);
  ctx.fillRect(padding, padding * 1.6, iconSize * 0.6, iconSize * 0.1);
  
  // AF text
  ctx.font = `bold ${size * 0.25}px Arial`;
  ctx.textAlign = 'center';
  ctx.fillText('AF', size / 2, size * 0.85);
  
  // Download
  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `icon${size}.png`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

// Generate all sizes
console.log('Generating icons...');
createIcon(16);
setTimeout(() => createIcon(48), 500);
setTimeout(() => createIcon(128), 1000);
console.log('Icons will be downloaded automatically');
