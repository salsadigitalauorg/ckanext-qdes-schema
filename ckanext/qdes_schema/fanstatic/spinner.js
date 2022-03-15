function removeLoader() {
    var $loaderEl = jQuery('.loader');
    $loaderEl.fadeOut(500, function () {
        // fadeOut complete. Remove the loading div
        $loaderEl.remove(); //makes page more lightweight
    });
}
jQuery(window).on('load', function () {
    removeLoader();
});
