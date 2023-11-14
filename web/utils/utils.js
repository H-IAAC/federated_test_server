const fs = require('fs'),
      consts = require('../utils/consts');

module.exports = {
    /**
     * @return {json}           Return content from ./config/algorithms.json
     */
    get_config: function () {

        if (fs.existsSync(consts.CONFIG_FILE_PATH)) {
            let rawdata = fs.readFileSync(consts.CONFIG_FILE_PATH);
            return JSON.parse(rawdata);
        }

        console.log("ERROR! Missing config file: " + consts.CONFIG_FILE_PATH);
        return {};
    }
}