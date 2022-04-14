package main

import (
	"fmt"
	"log"
	"strings"

	"gopkg.in/yaml.v2"
	"os"
	"io/ioutil"
)

type NameAndEmail struct {
	Name string
	Email string
	Restricted bool
}

type SubSystem struct {
	Subsystem string `subsystem`
	Labels struct {
		Name string `name`
		ReadyForMergeDeps []string `readyForMergeDeps`
		NewLabels string `newLabels`
		EmailLabel string `emailLabel`
	}
	Status string `status`
	RequiredApproval bool `requiredApproval`
	Maintainers []NameAndEmail `maintainers`
	Reviewers []NameAndEmail `reviewers`
	Paths struct {
		Includes []string
		IncludeRegexes []string
		Excludes []string
	}
	Scm string `scm`
	MailingList string `mailingList`
}

type SubSystems struct {
	SubSys []SubSystem `subsystems`
}

func CODEOWNERS_header() {
	fmt.Println("")
}

func main() {

	var subSystems SubSystems

	filename := os.Args[1]
	source, err := ioutil.ReadFile(filename)
	if err != nil {
		panic(err)
	}

	err = yaml.Unmarshal(source, &subSystems)
	if err != nil {
		log.Fatalf("error: %v", err)
	}

	CODEOWNERS_header()

	for count, entry := range subSystems.SubSys {
		// Do not write Disabled or unassigned entries into CODEOWNERS
		if entry.Status == "Disabled" || entry.Status == "Unassigned" {
			continue
		}

		if (count != 0) {
			fmt.Println("")
		}

		// Title
		if entry.RequiredApproval {
			fmt.Printf("[%s]\n", entry.Subsystem)
		} else {
			fmt.Printf("^[%s]\n", entry.Subsystem)
		}

		// Get list of maintainers that will be output below with files
		// 	Reviewers are NOT Code Maintainers
		//      TODO Lists cannot be Maintainers and should be transformed into groups
		var maintainers string
		for _, name := range entry.Maintainers {
			maintainers += name.Email + " "
		}
		maintainers = strings.TrimSpace(maintainers)

		// TODO No regex support (yet)

		// Files and email addresses
		for _, file := range entry.Paths.Includes {
			fmt.Printf("%s\t%s\n", file, maintainers)
		}
		for _, file := range entry.Paths.Excludes {
			fmt.Printf("^%s\t%s\n", file, maintainers)
		}
	}
}
