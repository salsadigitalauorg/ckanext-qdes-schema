jQuery(document).ready(function () {
    var $schemaFieldEl = jQuery('#field-schema');
    var $button = jQuery('#schema-validate');
    var toggleButton = function () {
        if ($schemaFieldEl.val() !== 'none') {
            $button.removeAttr('disabled');
        }
        else {
            $button.attr('disabled', 'disabled');
        }
    }
    toggleButton();
    $schemaFieldEl.on('change', toggleButton);
});
