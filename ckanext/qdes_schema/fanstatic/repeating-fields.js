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

    function collate_inputs(repeater_id, target_field_id, field_type) {
        var collated_values = [];

        jQuery('#' + repeater_id + ' ' + field_type).each(function() {
            collated_values.push(jQuery(this).val());
        });

        jQuery('#' + target_field_id).val(JSON.stringify(collated_values));
    }

    jQuery(document).on('blur', ".repeating-field textarea", function() {
        var repeater_id = jQuery(this).attr('id').replace('field-item-', '') + '-repeater';
        var target_field_id = jQuery(this).attr('id').replace('-item-', '-');
        var field_type = jQuery('#' + repeater_id).data('field-type');

        collate_inputs(repeater_id, target_field_id, field_type);
    });

});
