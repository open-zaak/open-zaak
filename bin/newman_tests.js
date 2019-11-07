var newman = require('newman');

const args = require('minimist')(process.argv.slice(2))

newman.run({
    collection: require('../tests.json'),
    environment: {
        "name": "test_environment",
        "values": [
            {
                "enabled": true,
                "key": "zrc_url",
                "value": args["zrc_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "drc_url",
                "value": args["drc_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "ztc_url",
                "value": args["ztc_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "brc_url",
                "value": args["brc_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "nrc_url",
                "value": args["nrc_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "ac_url",
                "value": args["ac_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "referentielijst_url",
                "value": args["referentielijst_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "mock_url",
                "value": args["mock_url"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "client_id",
                "value": args["client_id"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "secret",
                "value": args["secret"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "client_id_limited",
                "value": args["client_id_limited"],
                "type": "text"
            },
            {
                "enabled": true,
                "key": "secret_limited",
                "value": args["secret_limited"],
                "type": "text"
            },
        ]
    },
    reporters: ['cli']
}, function (err, summary) {
    if (err) { throw err; }

    var failures = summary.run.failures;

    if(failures.length == 0) {
        process.exit(0);
    }

    console.log('\n*********************************')
    console.log('FAILED REQUEST LOGS\n')

    var ids = [];
    for(i=0; i<failures.length; i++) {
        ids.push(failures[i].source.id);
    }

    var executions = summary.run.executions;
    for(i=0; i<executions.length; i++) {
        if(ids.includes(executions[i].item.id)) {
            console.log(executions[i].item.name);
            console.log('REQUEST:', executions[i].request);
            if(executions[i].response !== undefined) {
                console.log('RESPONSE:', executions[i].response.stream.toString(), '\n');
            }
        }
    }

    // Exit with code 1 because there were failures
    process.exit(1);
});
