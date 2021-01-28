(function ($) {
    $.fn.monthYearPicker = function () {
        var $pickerEl = $('.monthyear-picker');
        var d = new Date();
        var year = d.getFullYear();
        var month = ('0' + d.getMonth() + 1).slice(-2);
        var $el;
        var listernerSet = false;


        function _setPosition() {
            var height = $el.outerHeight();
            var offset = $el.parent().position();

            $pickerEl.css('top', offset.top + height + 10);
            _showPicker();
        }

        function _showPicker() {
            $pickerEl.addClass('show');
            document.addEventListener('click', _clickOutside);
        }

        function _hidePicker() {
            $pickerEl.removeClass('show');
            document.removeEventListener('click', _clickOutside);
            listernerSet = false;
        }

        function _clickOutside(e) {
            if (listernerSet) {
                if (!$pickerEl.is(e.target) && $pickerEl.has(e.target).length === 0) {
                    _hidePicker();
                }
            } else {
                listernerSet = true;
            }
        }

        function _getValue() {
            return $el.val();
        }

        function _setPickerValue($pickerEl, month, year) {
            $pickerEl.find('.month-picker').val(month);
            $pickerEl.find('.year-picker').val(year);
        }

        function _selected() {
            var monthVal = $pickerEl.find('.month-picker').val();
            var dateStr = $pickerEl.find('.year-picker').val();
            if (monthVal !== '00') {
                dateStr += '-' + monthVal;
            } else {
                dateStr += '-' + $el.attr('data-default-month');
            }

            $el.val(dateStr);
            $el.change();
            _hidePicker();
        }

        function _inFocus() {
            var value = _getValue();
            if (value !== '') {
                var monthValue = value.substring(5, value.length)
                _setPickerValue($pickerEl, monthValue ? monthValue : '00', value.substring(0, 4));
            } else {
                _setPickerValue($pickerEl, month, year);
            }
        }

        this.on('focus', function (e) {
            $el = $(this);

            _hidePicker();
            _inFocus();
            _setPosition();
        });

        $pickerEl.find('.monthyear-picker-action').on('click', function () {
            _selected();
        });

        $(document).keyup(function (e) {
            if (e.key === "Escape") {
                _hidePicker();
            }
        });
    }

    $(document).ready(function () {
        var $elDateInput = $('.temporal-coverage input');

        $elDateInput.monthYearPicker();

        // Toggle disabled of `to` based on the `from` value.
        $elDateInput.on('change', function () {
            if ($(this).attr('name') === 'temporal_coverage_from') {
                var $elDateTo = $(this).closest('.temporal-coverage').find('#to');
                if ($(this).val() !== '') {
                    $elDateTo.removeAttr('disabled');
                } else {
                    $elDateTo.attr('disabled', 'disabled');
                }
            }
        });
        $elDateInput.change();

        // Calendar click handler.
        $('.temporal-coverage .input-group-btn button').on('click', function () {
            var $dateEl = $(this).parent().parent().find('input');
            if (!$dateEl.is(':disabled')) {
                $(this).parent().parent().find('input').focus();
            }
        });

        var urlParams = new URLSearchParams(window.location.search);
        urlParams.forEach(function (value, key, parent) {
            if (key !== 'temporal_coverage_from' && key !== 'temporal_coverage_to') {
                $('.temporal-coverage').append('<input type="hidden" name="' + key + '" value="' + value + '" />');
            }
        });
    });
})($);



