
         var app = new Vue({
             el: '#kanbanapp',
             data: {
                 visible: 'createstory',
                 book_title: '',
                 characters: '',
                 storyline: '',
                 ages: '',
                 pages:{'A': ' ', 'B': ' ', 'C': ' ', 'D': ' ', 'E': ' ', 'F': ' ', 'G': ' ', 'H': ' ', 'I': ' ', 'J': ' ', 'K': ' ', 'L': ' ', 'M': ' ', 'N': ' ', 'O': ' ', 'P': ' ', 'Q': ' ', 'R': ' '},

                 intro_email_result: '',
                 rendered_story:false,
                 storybooks: '',


                 result: '',
                 type: '',
                 story_status: '',

                 name: '',
                 subject: '',
                 email_prompt: '',
                 task_type: '',
                 tasks: [],
                 emails: [],
                 templates: [],
                 new_id: '',
                 new_name: '',
                 new_subject: '',
                 new_email_prompt: '',
                 new_result: '',

                 job_title: '',
                 job_responsibilities: '',
                 job_requirements: '',
                 lists: ["blank"],
                 jobdescs: ["blank"],
                 new_job_title: '',
                 new_job_responsibilities: '',
                 new_job_requirements: '',
                 new_template_content: '',

                 task: '',
                 list_holding_these_tasks: '',
                 what_to_do: '',
                 list_name_for_deletion: '',
                 //id: '',
                 template_content: '',
                 list: '',
                 edit_id: '',
                 edit_type: '',
                 edit_result: '',
                 edit_job_title: '',
                 edit_job_responsibilities: '',
                 edit_job_requirements: '',
                 edit_name: '',
                 edit_subject: '',
                 edit_email_prompt: '',
                 edit_template_content: '',


             },
             delimiters: ['{','}'],

             methods: {
                 showModal(id) {
                     this.$refs[id].show()
                 },
                 hideModal(id) {
                     this.$refs[id].hide()
                 },

                 write_intro_email_button(){
                         this.story_status = "generating";
                         console.log('writing');
                         axios.post(this.baseURL+"write_intro_email",
                             {book_title : this.book_title, characters : this.characters, storyline : this.storyline, ages : this.ages}
                         )
                         .then(res => {
                             console.log(res)
                             this.result = res.data.result;
                             this.pages = res.data.pages;
                             this.rendered_story = true;
                             this.story_status = "generated";

                             const section = document.getElementById('bottom');
                             section.scrollIntoView();//{behavior: 'smooth'}
                             app.getTasks()
                         })
                 },


                 save_story(){
                         axios.post(this.baseURL+"save",
                             {pages : this.pages, book_title : this.book_title}
                         ).then(res => {
                             console.log(res)
                             alert('Saved result 🫡')
                             app.getTasks()
                         })
                 },



                 async getStories(){
                                       // var urlPath = window.location.pathname;
                                       // var urlPathParts = urlPath.split("/");
                                       // var discussion_id = urlPathParts[urlPathParts.length - 1];
                                       this.baseURL = window.location.protocol + "//" + window.location.host + "/";

                                    url = this.baseURL+'fetch_stories';
                                    console.log(url);
                                      axios({
                                        url: url,
                                        method: 'get'
                                      })
                                      .then(res => {
                                        this.storybooks = res.data.storybooks
                                        //this.lists = res.data.lists
                                      })

                                  },




                 // async getTasks(){
                 //     axios({
                 //       url: this.baseURL+'fetch',
                 //       method: 'get'
                 //     })
                 //     .then(res => {
                 //       this.results = res.data.results
                 //     })
                 //
                 // },


                  editEmail(id, name, subject, email_prompt, result, type){
                      console.log(id)
                        this.edit_id = id
                        this.edit_name = name
                        this.edit_subject = subject
                        this.edit_email_prompt = email_prompt
                        this.edit_result = result

                      axios.get(this.baseURL + type + "/" + id + "/")
                      .then(res => {
                          console.log(res.data)
                          this.new_id = id // res.data.editmember['id']
                          this.new_name = res.data.editmember['name']
                          this.new_subject = res.data.editmember['subject']
                          this.new_email_prompt = res.data.editmember['email_prompt']
                          this.new_result = res.data.editmember['result']
                          app.showModal('email-updation')
                      })
                    },


                  onUpdateEmail(){
                          axios.post(this.baseURL+"update_task/email",
                              { new_id : this.new_id, new_name : this.new_name, new_subject : this.new_subject, new_email_prompt : this.new_email_prompt, new_result : this.new_result}
                          )
                          .then(res => {
                              console.log(res)
                              this.new_name = '';
                              this.new_subject = '';
                              this.new_email_prompt = '';
                              this.new_result = '';
                              this.new_id = '';

                              app.hideModal('email-updation');
                              app.getTasks();
                          })
                  },

                 deleteTask(id){
                     if (window.confirm('Are you sure you want to delete this task?')) {
                         axios.get(this.baseURL+"delete_task/" + id)
                         .then(res => {
                             console.log(res)
                             alert('The task is gone 😮‍💨')
                             app.getTasks();
                         })
                     }
                 },

                 exportTask(id, type){
                     if (window.confirm('Export this task')) {
                         axios.get(this.baseURL+"export_task/" + type + "/" + id)
                         .then(res => {
                             console.log(res)
                             alert('The task has been exported to a csv 😉')
                             app.getTasks();
                         })
                     }
                 },

             exportAll(){
                     axios.get(this.baseURL+"export_all")
                     .then(res => {
                         console.log(res)
                         alert('The lists have been exported to a csv 😉')
                         app.getTasks();
                 })
             },

         },
             mounted: function(){
               this.getStories()
               //this.getTasks()
             }
         })
