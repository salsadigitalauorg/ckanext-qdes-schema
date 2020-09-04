(function ($) {
    $(document).ready(function () {
        'use strict';

        /**
         * Default designators.
         */
        var designators = [
            {label: 'years', symbol: 'Y', type: 'period', value: ''},
            {label: 'months', symbol: 'M', type: 'period', value: ''},
            {label: 'weeks', symbol: 'W', type: 'period', value: ''},
            {label: 'days', symbol: 'D', type: 'period', value: ''},
            {label: 'hours', symbol: 'H', type: 'time', value: ''},
            {label: 'minutes', symbol: 'M', type: 'time', value: ''},
            {label: 'seconds', symbol: 'S', type: 'time', value: ''},
        ]

        /**
         * Assign value to the element designators.
         *
         * @param el_designators
         *  The designator for the element.
         * @param label
         *  The label.
         * @param value
         *  The value.
         */
        var setDesignator = function (el_designators, label, value) {
            el_designators.forEach(function (item, index) {
                if (item.label === label) {
                    designators[index].value = value;
                }
            });
        }

        /**
         * Returns designator value with or without its symbol.
         *
         * @param el_designators
         *  The designator for the element.
         * @param label
         *  The label.
         * @param symbol
         *  True with symbol, else false without symbol.
         */
        var getDesignatorValue = function (el_designators, label, symbol) {
            var value = '';
            el_designators.forEach(function (item, index) {
                if (item.label === label && item.value !== '') {
                    value = symbol ? item.value + item.symbol : item.value;
                }
            });

            return value;
        }

        /**
         * Dump designators to ISO 8061 duration format.
         *
         * @param el_designators
         *  The designator for the element.
         * @returns {string}
         *  The duration format.
         */
        var dumpDesignators = function (el_designators) {
            var str = '';
            var has_period_notation = false;
            var has_time_notation = false;
            designators.forEach(function (item, index) {
                var value = getDesignatorValue(el_designators, item.label, true);

                if (value.length > 0 && item.type === 'period' && !has_period_notation) {
                    has_period_notation = true;
                    value = 'P' + value;
                }

                if (value.length > 0 && item.type === 'time' && !has_time_notation) {
                    has_time_notation = true;
                    value = 'T' + value;
                }

                str = str + value;
            });

            return str;
        }

        /**
         * Parses the iso8601 Duration string to object.
         *
         * @param iso8601Duration
         *  The duration string.
         *
         * @returns obj
         *  The designators obj.
         */
        var parseISO8601Duration = function (iso8601Duration) {
            var iso8601DurationRegex = /(-)?P(?:([.,\d]+)Y)?(?:([.,\d]+)M)?(?:([.,\d]+)W)?(?:([.,\d]+)D)?(?:T(?:([.,\d]+)H)?(?:([.,\d]+)M)?(?:([.,\d]+)S)?)?/;
            var matches = iso8601Duration.match(iso8601DurationRegex);
            var el_designators = designators;

            var result = {
                sign: matches[1] === undefined ? '+' : '-',
                years: matches[2] === undefined ? '' : matches[2],
                months: matches[3] === undefined ? '' : matches[3],
                weeks: matches[4] === undefined ? '' : matches[4],
                days: matches[5] === undefined ? '' : matches[5],
                hours: matches[6] === undefined ? '' : matches[6],
                minutes: matches[7] === undefined ? '' : matches[7],
                seconds: matches[8] === undefined ? '' : matches[8]
            }

            el_designators.forEach(function (item, index) {
                el_designators[index].value = result[item.label];
            });

            return el_designators;
        }

        // Listen to duration fields.
        $(document).on('blur', '.iso-8601-duration-field input', function () {
            var $wrapper = $(this).parents('.iso-8601-duration-field-wrapper');
            var field_name = $wrapper.data('duration-fieldname');
            var $el = $wrapper.find('#field-' + field_name);
            var current_designator = $(this).attr('name').replace(field_name + '_', '');

            setDesignator(duration_field_designators[field_name], current_designator, $(this).val());

            $el.val(dumpDesignators(duration_field_designators[field_name]));
        });

        // Setup the duration field.
        var duration_field_designators = [];
        $('.iso-8601-duration-field-wrapper').each(function () {
            var $el_wrapper = $(this);
            var field_name = $el_wrapper.data('duration-fieldname');
            var $el = $el_wrapper.find('#field-' + field_name);

            if (field_name.length > 0) {
                // Parse the duration and put them to respected field.
                duration_field_designators[field_name] = designators;

                if ($el.val().length > 0) {
                    var has_existing_value = false;
                    duration_field_designators[field_name] = parseISO8601Duration($el.val());

                    duration_field_designators[field_name].forEach(function (item, index) {
                        var $el_designator = $el_wrapper.find('#field-' + field_name + '-' + item.label);

                        // On setup, when the field already a value, leave it,
                        // it is an value from form validation error.
                        if ($el_designator.val().length > 0) {
                            has_existing_value = true;
                        }
                        else {
                            $el_designator.val(item.value);
                        }
                    });

                    // If has_existing_value is true, trigger the blur effect on each designator fields,
                    // at this stage the duration_field_designators[field_name] won't have all information.
                    if (has_existing_value) {
                        $el_wrapper.find('.iso-8601-duration-field input').each(function () {
                            console.log($(this).attr('id'));
                            $(this).blur();
                        });
                    }
                }
            }
        });
    });
}(jQuery));
