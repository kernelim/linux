package main

import (
	"io/ioutil"
	"log"
	"os"
	"strings"

	"gopkg.in/yaml.v2"
)

type NameAndEmail struct {
	Name string
	Email string
	Restricted bool
	Gluser string
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
	DevelSst []string `devel-sst`
	QeSst []string `qe-sst`
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

func contains(names []string, name string) bool {
	for _, a := range names {
		if a == name {
			return true
		}
	}
	return false
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

	//
	// Check for duplicate Subsystem 'Label' entries
	//
	com := make(map[string]string)
	for _, s := range subSystems.SubSys {
		if _, ok := com[s.Labels.Name]; ok {
			if s.Labels.Name != "redhat" {
				log.Fatalf("error: Found duplicate Subsystem Label '%s' for entries '%s' and '%s'", s.Labels.Name, s.Subsystem, com[s.Labels.Name])
			}
		}
		com[s.Labels.Name] = s.Subsystem
	}

	//
	// check for machine-readable Alphabetical order
	//
	last := subSystems.SubSys[0]
	for count, s := range subSystems.SubSys {
		if count == 0 {
			continue
		}
		last = subSystems.SubSys[count-1]
		if strings.ToUpper(s.Subsystem) < strings.ToUpper(last.Subsystem) {
			if !strings.HasPrefix(last.Subsystem, "RHEL") {
				log.Fatalf("error: entries '%s' and '%s' are not in alphabetical order.\n", s.Subsystem, last.Subsystem)
			}
		}
	}

	//
	// General data verification
	//

	for _, s := range subSystems.SubSys {
		// check that devel-sst is set
		if s.DevelSst == nil {
			log.Fatalf("error: '%s' is missing a devel-sst entry", s.Subsystem)
		}
		// check that qe-sst is set
		if s.QeSst == nil {
			log.Fatalf("error: '%s' is missing a qe-sst entry", s.Subsystem)
		}
		// check that the devel-sst is valid
		for _, sst := range s.DevelSst {
			if !contains(validSSTNames, sst) {
				log.Fatalf("error: '%s' devel-sst entry (%s) is not valid", s.Subsystem, sst)
			}
		}
		// check that the qe-sst is valid
		for _, sst := range s.QeSst {
			if !contains(validSSTNames, sst) {
				log.Fatalf("error: '%s' qe-sst entry (%s) is not valid", s.Subsystem, sst)
			}
		}
	}
}
