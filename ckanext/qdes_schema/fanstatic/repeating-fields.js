jQuery(document).ready(function () {
    'use strict';

    jQuery('.repeating-field').repeater({

        show: function () {
            jQuery(this).show();
        },
        hide: function (deleteElement) {
            if(confirm('Are you sure you want to remove this item?')) {
                jQuery(this).hide(deleteElement);
            }
        },
        ready: function (setIndexes) {

        },
        isFirstItemUndeletable: true
    });

    jQuery('.collate-inputs').on('click', function() {

        var repeater_id = jQuery(this).data('repeater-id');
        var target_field_id = jQuery(this).data('target-field-id');
        var field_type = jQuery(this).data('field-type');

        // var all = $('#' + repeater_id).repeaterVal();

        var collated_values = [];

        jQuery('#' + repeater_id + ' ' + field_type).each(function() {
            collated_values.push(jQuery(this).val());
        });

        jQuery('#' + target_field_id).val(JSON.stringify(collated_values));

        return false;
    });

});
