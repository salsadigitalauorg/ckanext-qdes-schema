jQuery(document).ready(function () {

  jQuery('button[class="acc-heading"]').keyup(function (e) {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      e.target.parentNode.querySelector("input[type]").click();
      e.preventDefault();
    }
  });

});