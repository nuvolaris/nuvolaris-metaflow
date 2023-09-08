package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

func Main(args map[string]interface{}) map[string]interface{} {
	env := copyEnvironment()

	if args["command"] != nil {
		command := args["command"].([]interface{})
		fmt.Println(command)

		parts := strings.Fields(command[0].(string))
		cmd := exec.Command(parts[0], parts[1:]...)

		if args["environment_variables"] != nil {
			envVars := args["environment_variables"].(map[string]interface{})
			for k, v := range envVars {
				env[k] = v.(string)
			}
			cmd.Env = environmentToList(envVars)
		}

		output, err := cmd.CombinedOutput()

		result := map[string]interface{}{
			"mf_process_status":   "failed",
			"mf_process_ret_code": cmd.ProcessState.ExitCode(),
			"mf_process_stdout":   string(output),
		}

		if err == nil {
			result["mf_process_status"] = "success"
			result["mf_process_stdout"] = string(output)
		} else {
			result["mf_process_stderr"] = string(err.Error())
		}

		// Print the result or use it as needed.
		fmt.Println(result)
		return result
	} else {
		result := map[string]interface{}{
			"mf_process_status": "failed",
		}
		return result
	}
}

func copyEnvironment() map[string]string {
	env := make(map[string]string)
	for _, e := range os.Environ() {
		pair := strings.SplitN(e, "=", 2)
		if len(pair) == 2 {
			env[pair[0]] = pair[1]
		}
	}
	return env
}

func environmentToList(env map[string]interface{}) []string {
	var envList []string
	for key, value := range env {
		envList = append(envList, key+"="+value.(string))
	}
	return envList
}
