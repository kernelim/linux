package main

// This program outputs the name, email, and GitLab username based on a search
// query.  For example,
//
// searchowners ../info/owners.yaml prarit
//
// would output
//
// Name: Prarit Bhargava
// Email: prarit@redhat.com
// GitLab User: prarit
//

import (
	"fmt"
	"log"
	"regexp"

	"gopkg.in/yaml.v2"
	"os"
	"io/ioutil"
)

type NameAndEmail struct {
	Name string `name`
	Email string `email`
	GLUser string `gluser`
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

var matchesNames []NameAndEmail

func match(matchString string, name NameAndEmail) bool {

	// do not report the same entry twice
	for _,entry := range matchesNames {
		if entry == name {
			return true
		}
	}

	re := regexp.MustCompile(matchString)
	m := re.FindStringSubmatch(name.Name + " " + name.Email + " " + name.GLUser)
	if len(m) > 0 {
		fmt.Println("Name:", name.Name)
		fmt.Println("Email:", name.Email)
		fmt.Println("GitLab User:", name.GLUser, "\n")
		// add the entry to the reported names so it is not reported again
		matchesNames = append(matchesNames, name)
		return true
	}
	return false
}

func main() {

	var subSystems SubSystems

	if len(os.Args) != 3 {
		fmt.Println("Usage: searchowners <location of owners.yaml> <search string>\n")
		fmt.Println("First argument is the location of the owners.yaml file, and the second arguments is the search string.")
		fmt.Println("  ex) findowners ../info/owners.yaml prarit")
		os.Exit(1)
	}

	filename := os.Args[1]
	source, err := ioutil.ReadFile(filename)
	if err != nil {
		fmt.Printf("Unable to open %s: %s\n", filename, err)
		os.Exit(1)
	}


	err = yaml.Unmarshal(source, &subSystems)
	if err != nil {
		log.Fatalf("error: %v", err)
	}

	for _, entry := range subSystems.SubSys {
		for _, name := range entry.Maintainers {
			match(os.Args[2], name)
		}

		for _, name := range entry.Reviewers {
			match(os.Args[2], name)
		}
	}
}
