package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"strings"
	"regexp"

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
	JiraComponent string `jiraComponent`
	DevelSst []string `devel-sst`
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
	r := regexp.MustCompile(`[-.\*]`)
	validIncludeFiles := []string {"makefile",
				       "Makefile",
				       "Kconfig",
				      }
	for _, s := range subSystems.SubSys {
		// check that jiraComponent is set
		if s.JiraComponent == "" {
			log.Fatalf("error: '%s' is missing a jiraComponent entry", s.Subsystem)
		}
		// check that devel-sst is set
		if s.DevelSst == nil {
			log.Fatalf("error: '%s' is missing a devel-sst entry", s.Subsystem)
		}
		// check that the devel-sst is valid
		for _, sst := range s.DevelSst {
			if !contains(validSSTNames, sst) {
				log.Fatalf("error: '%s' devel-sst entry (%s) is not valid", s.Subsystem, sst)
			}
		}

		if s.Maintainers != nil {
			if len(s.Maintainers) == 0 {
				log.Fatalf("error: '%s' must have a maintainer listed", s.Subsystem)
			}
			for _, maintainer := range s.Maintainers {
				// Name Email Gluser
				if maintainer.Name == "" || maintainer.Email == "" || maintainer.Gluser == "" {
					log.Fatalf("error: '%s' maintainer fields (name, email, and gluser) cannot be empty", s.Subsystem)
				}
			}
			for _, reviewer := range s.Reviewers {
				// Name Email Gluser
				if reviewer.Name == "" || reviewer.Email == "" || reviewer.Gluser == "" {
					log.Fatalf("error: '%s' reviewer fields (name, email, and gluser) cannot be empty", s.Subsystem)
				}
			}
		}

		// check for '/' at the end of directories
		for _, include := range s.Paths.Includes {
			parts := strings.SplitAfter(include, "/")
			// This implies the last char before the newline was
			// a '/'.  This is good, we can skip.
			if parts[len(parts)-1] == "" {
				continue
			}
			if parts[0] == "Documentation/" {
				continue
			}
			file := parts[len(parts)-1]
			matches := r.FindAllString(file, -1)
			if matches != nil {
				continue
			}
			if contains(validIncludeFiles, file) {
				continue
			}
			log.Fatalf("error: '%s:%s' is a bad includes entry (missing directory '/'?)", s.Subsystem, include)
		}
	}

	// The maintainer and reviewer data has been verified.  Now, make sure
	// user entries are consistent (ie, gluser prarit isn't gluser PraritB
	// in another entry).  This is tricky to do as users could have two
	// names, two email addresses or two GitLab user names.  The only way
	// to "verify" the data is to cross-reference it.

	type checkName struct {
		string1 string
		string2 string
	}

	emailList := make(map[string]checkName)
	gluserList := make(map[string]checkName)
	nameList := make(map[string]checkName)
	for _, s := range subSystems.SubSys {
		if len(s.Maintainers) == 0 {
			log.Fatalf("%s has no maintainers listed\n", s.Subsystem)
		}
		for _, maintainer := range s.Maintainers {
			if maintainer.Email == "jforbes@fedoraproject.org" {
				// we know that Justin has both a redhat and fedora account listed
				continue
			}
			if _, exists := emailList[maintainer.Email]; exists {
				if maintainer.Name != emailList[maintainer.Email].string1 ||
				   maintainer.Gluser != emailList[maintainer.Email].string2 {
					   fmt.Println(s.Subsystem, maintainer, emailList[maintainer.Email])
					log.Fatalf("error: 1) Multiple maintainer entries found for user %s[%s:%s]\n", maintainer.Name, maintainer.Email, maintainer.Gluser)
				}
			} else {
				emailList[maintainer.Email] = checkName{ string1:maintainer.Name, string2: maintainer.Gluser }
			}

			if _, exists := gluserList[maintainer.Gluser]; exists {
				if maintainer.Email != gluserList[maintainer.Gluser].string1 ||
				   maintainer.Name != gluserList[maintainer.Gluser].string2 {
					   fmt.Println(s.Subsystem, maintainer, gluserList[maintainer.Gluser])
					log.Fatalf("error: 2) Multiple maintainer entries found for user %s[%s:%s]\n", maintainer.Name, maintainer.Email, maintainer.Gluser)
				}
			} else {
				gluserList[maintainer.Gluser] = checkName{ string1:maintainer.Email, string2: maintainer.Name }
			}

			if _, exists := nameList[maintainer.Name]; exists {
				if maintainer.Email != nameList[maintainer.Name].string1 ||
				   maintainer.Gluser != nameList[maintainer.Name].string2 {
					   fmt.Println(s.Subsystem, maintainer, nameList[maintainer.Name])
					log.Fatalf("error: 3) Multiple maintainer entries found for user %s[%s:%s]\n", maintainer.Name, maintainer.Email, maintainer.Gluser)
				}
			} else {
				nameList[maintainer.Name] = checkName{ string1:maintainer.Email, string2: maintainer.Gluser }
			}
		}
		for _, reviewer := range s.Reviewers {
			if reviewer.Email == "jforbes@fedoraproject.org" {
				// we know that Justin has both a redhat and fedora account listed
				continue
			}
			if _, exists := emailList[reviewer.Email]; exists {
				if reviewer.Name != emailList[reviewer.Email].string1 ||
				   reviewer.Gluser != emailList[reviewer.Email].string2 {
					   fmt.Println(s.Subsystem, reviewer, emailList[reviewer.Email])
					log.Fatalf("error: 1) Multiple reviewer entries found for user %s[%s:%s]\n", reviewer.Name, reviewer.Email, reviewer.Gluser)
				}
			} else {
				emailList[reviewer.Email] = checkName{ string1:reviewer.Name, string2: reviewer.Gluser }
			}

			if _, exists := gluserList[reviewer.Gluser]; exists {
				if reviewer.Email != gluserList[reviewer.Gluser].string1 ||
				   reviewer.Name != gluserList[reviewer.Gluser].string2 {
					   fmt.Println(s.Subsystem, reviewer, gluserList[reviewer.Gluser])
					log.Fatalf("error: 2) Multiple reviewer entries found for user %s[%s:%s]\n", reviewer.Name, reviewer.Email, reviewer.Gluser)
				}
			} else {
				gluserList[reviewer.Gluser] = checkName{ string1:reviewer.Email, string2: reviewer.Name }
			}

			if _, exists := nameList[reviewer.Name]; exists {
				if reviewer.Email != nameList[reviewer.Name].string1 ||
				   reviewer.Gluser != nameList[reviewer.Name].string2 {
					   fmt.Println(s.Subsystem, reviewer, nameList[reviewer.Name])
					log.Fatalf("error: 3) Multiple reviewer entries found for user %s[%s:%s]\n", reviewer.Name, reviewer.Email, reviewer.Gluser)
				}
			} else {
				nameList[reviewer.Name] = checkName{ string1:reviewer.Email, string2: reviewer.Gluser }
			}
		}

	}


}
