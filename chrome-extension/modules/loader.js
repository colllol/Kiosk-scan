/**
 * Module Loader
 * Loads all modules in correct order before content.js
 */

(function() {
  'use strict';

  console.log('[ModuleLoader] Loading modules...');

  // Load modules synchronously in correct order
  const modules = [
    'url-scanner.js',
    'form-filler.js', 
    'dialog-handler.js',
    'component-workflow.js',
    'overlay-handler.js'
  ];

  // Function to load a module
  function loadModule(moduleName) {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL(`modules/${moduleName}`);
    script.onload = function() {
      console.log(`[ModuleLoader] Loaded: ${moduleName}`);
    };
    script.onerror = function() {
      console.error(`[ModuleLoader] Failed to load: ${moduleName}`);
    };
    document.head.appendChild(script);
  }

  // Load all modules
  modules.forEach(loadModule);

  console.log('[ModuleLoader] All modules loaded');
})();