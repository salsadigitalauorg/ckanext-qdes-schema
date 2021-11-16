jQuery(document).ready(function () {
      
  document.addEventListener('keyup', function (e) {
    console.log(e.key);
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      document.activeElement.parentNode.querySelector("input[type]").checked = "true";
    };

    e.preventDefault();
  });
});