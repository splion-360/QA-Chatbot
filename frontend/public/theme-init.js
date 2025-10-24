(function() {
  try {
    var colorScheme = localStorage.getItem('mui-color-scheme') || 'dark';
    document.documentElement.setAttribute('data-mui-color-scheme', colorScheme);
    document.documentElement.style.colorScheme = colorScheme;
  } catch (e) {
    document.documentElement.setAttribute('data-mui-color-scheme', 'dark');
    document.documentElement.style.colorScheme = 'dark';
  }
})();