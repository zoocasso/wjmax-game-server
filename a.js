var formdata = new FormData();
formdata.append('file', upload_xlsx_file.files[0])


fetch('/xlsx_parsing',{
    method:'POST',
    body:formdata,
})
.then((response) => console.log(response.json()))
.then(data => console.log(data))