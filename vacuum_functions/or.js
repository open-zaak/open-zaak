// The Logius API design rules make use of the function `or`, which vacuum does not
// support
function getSchema() {
  return {
    name: "or",
    description: "Passes if any configured property exists."
  };
}

function runRule(input) {
  const properties = context.rule.then.functionOptions.properties || [];

  for (const property of properties) {
    if (Object.prototype.hasOwnProperty.call(input, property)) {
      return [];
    }
  }

  return [
    {
      message: "None of the required properties were found."
    }
  ];
}
