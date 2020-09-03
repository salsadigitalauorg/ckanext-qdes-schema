jQuery(document).ready(function () {
    'use strict';

    function parseISO8601Duration(iso8601Duration) {
        var iso8601DurationRegex = /(-)?P(?:([.,\d]+)Y)?(?:([.,\d]+)M)?(?:([.,\d]+)W)?(?:([.,\d]+)D)?T(?:([.,\d]+)H)?(?:([.,\d]+)M)?(?:([.,\d]+)S)?/;

        var matches = iso8601Duration.match(iso8601DurationRegex);

        return {
            sign: matches[1] === undefined ? '+' : '-',
            years: matches[2] === undefined ? 0 : matches[2],
            months: matches[3] === undefined ? 0 : matches[3],
            weeks: matches[4] === undefined ? 0 : matches[4],
            days: matches[5] === undefined ? 0 : matches[5],
            hours: matches[6] === undefined ? 0 : matches[6],
            minutes: matches[7] === undefined ? 0 : matches[7],
            seconds: matches[8] === undefined ? 0 : matches[8]
        }
    }

    console.log(parseISO8601Duration('P3Y6M4DT12H'))

});
