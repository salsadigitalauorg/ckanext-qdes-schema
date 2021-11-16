jQuery(document).ready(function () {
      
  document.addEventListener('keyup', function (e) {
    console.log(e.key);
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      var checked = document.activeElement.parentNode.querySelector("input[type]").checked;
      document.activeElement.parentNode.querySelector("input[type]").checked = !checked;
    };

    e.preventDefault();
  });
});