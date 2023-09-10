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
		args_c := args["command"].([]interface{})

		command := parseArguments(args_c)
		fmt.Println(command)

		cmd := exec.Command("/bin/bash", "-c", command)

		if args["environment_variables"] != nil {
			envVars := args["environment_variables"].(map[string]interface{})
			for k, v := range envVars {
				env[k] = v.(string)
			}
			cmd.Env = prepareEnvironment(env)
		}

		output, err := cmd.CombinedOutput()

		result := map[string]interface{}{
			"mf_process_status":   "success",
			"mf_process_ret_code": cmd.ProcessState.ExitCode(),
			"mf_process_stdout":   string(output),
		}

		if err == nil {
			result["mf_process_stderr"] = ""
		} else {
			result["mf_process_stderr"] = err
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

func prepareEnvironment(env map[string]string) []string {
	var envList []string
	for key, value := range env {
		envList = append(envList, key+"="+value)
	}
	// we add python environment variable required by mf
	envList = append(envList, "DEFAULT_PYTHON_EXECUTABLE=python3")
	return envList
}

func parseArguments(args_c []interface{}) string {
	var command string
	for k := range args_c {
		command = command + " " + args_c[k].(string)
	}
	return command
}
