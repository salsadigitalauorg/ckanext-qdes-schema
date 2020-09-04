jQuery(document).ready(function () {
    'use strict';

    jQuery('.repeating-field').repeater({

        show: function () {
            // Check to see if there is any select elements with an autocomplete data module
            jQuery(this).find('select[data-module="autocomplete"]').map(function (index, select) {
                // Initialize autocomplete data for select element
                ckan.module.initializeElement(select);
            });
            jQuery(this).show();
        },
        hide: function (deleteElement) {
            if (confirm('Are you sure you want to remove this item?')) {
                // Remove value and trigger events
                jQuery(this).find('.form-control, select[data-module="autocomplete"]').val('').blur().change();
                jQuery(this).hide(deleteElement);
            }
        },
        ready: function (setIndexes) {

        },
        isFirstItemUndeletable: true
    });

    function collate_inputs(repeater_id, target_field_id, field_type) {
        var collated_values = [];

        jQuery('#' + repeater_id + ' ' + field_type + '.form-control, #' + repeater_id + ' ' + field_type + '[data-module="autocomplete"]').each(function () {
            var value = jQuery(this).val();

            if (value && value.trim().length > 0) {
                collated_values.push(jQuery(this).val());
            }
        });

        if (collated_values.length > 0) {
            jQuery('#' + target_field_id).val(JSON.stringify(collated_values));
        }
        else {
            jQuery('#' + target_field_id).val('');
        }
    }

    function update_repeater_fields(element) {
        var field_name = jQuery(element).data('field-name');
        var repeater_id = field_name + '-repeater';
        var target_field_id = 'field-' + field_name;
        var field_type = jQuery('#' + repeater_id).data('field-type');

        collate_inputs(repeater_id, target_field_id, field_type);
    }

    // Listen to repeatable fields.
    jQuery(document).on('blur', ".repeating-field .form-control", function () {
        update_repeater_fields(this);
    });
    jQuery(document).on('change', ".repeating-field select[data-module='autocomplete']", function () {
        update_repeater_fields(this);
    });

    // On load trigger the on change/blur for repeatable fields,
    // otherwise required fields won't have value by default.
    jQuery(".repeating-field .form-control").blur();
    jQuery(".repeating-field select[data-module='autocomplete']").change();
});
